# -*- coding: utf-8 -*-
from __future__ import annotations

import argparse
import csv
from pathlib import Path
import os
import requests
from dataclasses import dataclass

import psycopg2


@dataclass
class Position:
    qty: float = 0.0
    avg_price: float = 0.0
    realized_pnl: float = 0.0
    trades: int = 0
    wins: int = 0
    losses: int = 0
    equity_curve: list[tuple[str, float]] | None = None
    max_drawdown: float = 0.0


def dsn() -> str:
    return (
        f"postgresql://{os.getenv('DB_USER', 'finam')}:{os.getenv('DB_PASSWORD', 'finam')}"
        f"@{os.getenv('DB_HOST', '127.0.0.1')}:{os.getenv('DB_PORT', '5432')}/{os.getenv('DB_NAME', 'finam')}"
    )


def load_last_prices(symbols: list[str]) -> dict[str, float]:
    sql = """
        SELECT DISTINCT ON (symbol) symbol, close_price
        FROM market_data
        WHERE symbol = ANY(%s)
        ORDER BY symbol, ts DESC
    """
    with psycopg2.connect(dsn()) as conn:
        with conn.cursor() as cur:
            cur.execute(sql, (symbols,))
            return {str(symbol): float(price) for symbol, price in cur.fetchall()}


def send_telegram(text: str) -> None:
    token = (os.getenv("TG_BOT_TOKEN") or os.getenv("TG_TOKEN") or "").strip()
    chat_id = os.getenv("TG_CHAT_ID", "").strip()
    if not token or not chat_id:
        print("TELEGRAM_SKIPPED reason=missing_token_or_chat_id")
        return

    try:
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        r = requests.post(url, json={"chat_id": chat_id, "text": text}, timeout=15)
        r.raise_for_status()
        print("TELEGRAM_SENT")
    except Exception as exc:
        print(f"TELEGRAM_SKIPPED reason={type(exc).__name__}:{exc}")


def load_trades(symbols: list[str], run_id: str | None = None):
    sql = """
        SELECT symbol, side, qty, price, ts
        FROM trades
        WHERE symbol = ANY(%s)
          AND raw_json->>'paper_only' = 'true'
          AND (%s IS NULL OR raw_json->>'run_id' = %s)
        ORDER BY symbol, ts ASC
    """
    with psycopg2.connect(dsn()) as conn:
        with conn.cursor() as cur:
            cur.execute(sql, (symbols, run_id, run_id))
            return cur.fetchall()


def apply_trade(pos: Position, side: str, qty: float, price: float, ts=None) -> None:
    if pos.equity_curve is None:
        pos.equity_curve = []
    pos.trades += 1

    signed_qty = qty if side == "BUY" else -qty

    # Русский комментарий: если позиция нулевая или наращиваем ту же сторону.
    if pos.qty == 0 or (pos.qty > 0 and signed_qty > 0) or (pos.qty < 0 and signed_qty < 0):
        new_qty = pos.qty + signed_qty
        if new_qty != 0:
            pos.avg_price = ((abs(pos.qty) * pos.avg_price) + (abs(signed_qty) * price)) / abs(new_qty)
        pos.qty = new_qty
        return

    # Русский комментарий: закрываем встречной сделкой.
    closing_qty = min(abs(pos.qty), abs(signed_qty))

    if pos.qty > 0:
        pnl = (price - pos.avg_price) * closing_qty
    else:
        pnl = (pos.avg_price - price) * closing_qty

    pos.realized_pnl += pnl
    pos.equity_curve.append((str(ts), float(pos.realized_pnl)))
    pos.max_drawdown = min(pos.max_drawdown, calc_drawdown(pos.equity_curve))

    if pnl > 0:
        pos.wins += 1
    elif pnl < 0:
        pos.losses += 1

    remaining_qty = pos.qty + signed_qty

    if remaining_qty == 0:
        pos.qty = 0.0
        pos.avg_price = 0.0
    elif (pos.qty > 0 and remaining_qty > 0) or (pos.qty < 0 and remaining_qty < 0):
        pos.qty = remaining_qty
    else:
        # Русский комментарий: переворот позиции.
        pos.qty = remaining_qty
        pos.avg_price = price


def calc_drawdown(curve: list[tuple[str, float]]) -> float:
    peak = 0.0
    max_dd = 0.0
    for _ts, equity in curve:
        peak = max(peak, equity)
        dd = equity - peak
        max_dd = min(max_dd, dd)
    return max_dd


def write_curve_csv(path: str, positions: dict[str, Position]) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["symbol", "ts", "realized_equity"])
        for symbol, pos in positions.items():
            for ts, equity in pos.equity_curve or []:
                w.writerow([symbol, ts, round(equity, 6)])


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--symbols", nargs="+", required=True)
    parser.add_argument("--run-id", required=False)
    parser.add_argument("--curve-csv", default="reports/replay_pnl_curve.csv")
    parser.add_argument("--telegram", action="store_true")
    args = parser.parse_args()

    rows = load_trades(args.symbols, run_id=args.run_id)
    last_prices = load_last_prices(args.symbols)
    positions = {symbol: Position() for symbol in args.symbols}

    for symbol, side, qty, price, _ts in rows:
        apply_trade(
            positions[str(symbol)],
            str(side).upper(),
            float(qty),
            float(price),
            ts=_ts,
        )

    lines: list[str] = []
    lines.append("REPLAY_PNL_REPORT")

    total_realized = 0.0
    total_unrealized = 0.0
    total_equity = 0.0
    total_trades = 0

    for symbol in args.symbols:
        p = positions[symbol]
        closed = p.wins + p.losses
        winrate = (p.wins / closed * 100.0) if closed else 0.0
        last_price = last_prices.get(symbol, 0.0)
        if p.qty > 0:
            unrealized = (last_price - p.avg_price) * abs(p.qty)
        elif p.qty < 0:
            unrealized = (p.avg_price - last_price) * abs(p.qty)
        else:
            unrealized = 0.0

        equity_pnl = p.realized_pnl + unrealized

        total_realized += p.realized_pnl
        total_unrealized += unrealized
        total_equity += equity_pnl
        total_trades += p.trades

        lines.append(
            "SYMBOL_PNL "
            f"symbol={symbol} "
            f"trades={p.trades} "
            f"closed_trades={closed} "
            f"wins={p.wins} "
            f"losses={p.losses} "
            f"winrate={round(winrate, 2)}% "
            f"realized_pnl={round(p.realized_pnl, 6)} "
            f"last_price={round(last_price, 6)} "
            f"open_qty={round(p.qty, 6)} "
            f"avg_price={round(p.avg_price, 6)} "
            f"unrealized_pnl={round(unrealized, 6)} "
            f"equity_pnl={round(equity_pnl, 6)} "
            f"max_drawdown={round(p.max_drawdown, 6)}"
        )

    lines.append("TOTAL_PNL")
    lines.append(f"symbols={len(args.symbols)}")
    lines.append(f"trades={total_trades}")
    lines.append(f"realized_pnl={round(total_realized, 6)}")
    lines.append(f"unrealized_pnl={round(total_unrealized, 6)}")
    total_max_drawdown = sum(p.max_drawdown for p in positions.values())
    lines.append(f"equity_pnl={round(total_equity, 6)}")
    lines.append(f"sum_symbol_max_drawdown={round(total_max_drawdown, 6)}")
    lines.append(f"curve_csv={args.curve_csv}")
    lines.append("STATUS=OK")

    write_curve_csv(args.curve_csv, positions)

    report = "\n".join(lines)
    print(report)

    if args.telegram:
        send_telegram(report)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
