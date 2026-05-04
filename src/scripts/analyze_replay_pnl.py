# -*- coding: utf-8 -*-
from __future__ import annotations

import argparse
import os
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


def dsn() -> str:
    return (
        f"postgresql://{os.getenv('DB_USER', 'finam')}:{os.getenv('DB_PASSWORD', 'finam')}"
        f"@{os.getenv('DB_HOST', '127.0.0.1')}:{os.getenv('DB_PORT', '5432')}/{os.getenv('DB_NAME', 'finam')}"
    )


def load_trades(symbols: list[str]):
    sql = """
        SELECT symbol, side, qty, price, ts
        FROM trades
        WHERE symbol = ANY(%s)
          AND raw_json->>'paper_only' = 'true'
        ORDER BY symbol, ts ASC
    """
    with psycopg2.connect(dsn()) as conn:
        with conn.cursor() as cur:
            cur.execute(sql, (symbols,))
            return cur.fetchall()


def apply_trade(pos: Position, side: str, qty: float, price: float) -> None:
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


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--symbols", nargs="+", required=True)
    args = parser.parse_args()

    rows = load_trades(args.symbols)
    positions = {symbol: Position() for symbol in args.symbols}

    for symbol, side, qty, price, _ts in rows:
        apply_trade(
            positions[str(symbol)],
            str(side).upper(),
            float(qty),
            float(price),
        )

    print("REPLAY_PNL_REPORT")

    total_pnl = 0.0
    total_trades = 0

    for symbol in args.symbols:
        p = positions[symbol]
        closed = p.wins + p.losses
        winrate = (p.wins / closed * 100.0) if closed else 0.0
        total_pnl += p.realized_pnl
        total_trades += p.trades

        print(
            "SYMBOL_PNL "
            f"symbol={symbol} "
            f"trades={p.trades} "
            f"closed_trades={closed} "
            f"wins={p.wins} "
            f"losses={p.losses} "
            f"winrate={round(winrate, 2)}% "
            f"realized_pnl={round(p.realized_pnl, 6)} "
            f"open_qty={round(p.qty, 6)} "
            f"avg_price={round(p.avg_price, 6)}"
        )

    print("TOTAL_PNL")
    print(f"symbols={len(args.symbols)}")
    print(f"trades={total_trades}")
    print(f"realized_pnl={round(total_pnl, 6)}")
    print("STATUS=OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
