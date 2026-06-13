#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import argparse
from collections import deque
from datetime import timezone, timedelta
import os

import psycopg
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb


MSK = timezone(timedelta(hours=3))


DDL = """
CREATE TABLE IF NOT EXISTS analytics_closed_trades_v1 (
    trade_id text PRIMARY KEY,
    symbol text NOT NULL,
    strategy text,
    side text NOT NULL,
    qty double precision NOT NULL,
    entry_ts timestamptz NOT NULL,
    exit_ts timestamptz NOT NULL,
    entry_price double precision NOT NULL,
    exit_price double precision NOT NULL,
    pnl_points double precision NOT NULL,
    entry_fill_id text,
    exit_fill_id text,
    entry_signal_id text,
    exit_signal_id text,
    exit_reason text,
    hour_msk integer,
    weekday text,
    session text,
    source text NOT NULL,
    raw jsonb NOT NULL DEFAULT '{}'::jsonb,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_analytics_closed_trades_v1_symbol_exit_ts
ON analytics_closed_trades_v1(symbol, exit_ts);

CREATE INDEX IF NOT EXISTS idx_analytics_closed_trades_v1_symbol_strategy_exit_ts
ON analytics_closed_trades_v1(symbol, strategy, exit_ts);
"""


def session_ru(hour: int | None) -> str:
    if hour is None:
        return "неизвестно"
    if 7 <= hour < 10:
        return "утро_мск"
    if 10 <= hour < 15:
        return "московская_середина"
    if 15 <= hour < 19:
        return "вечерняя_сессия"
    return "вне_основной_сессии"


def norm_strategy(symbol: str, raw: str | None) -> str:
    if raw and raw not in ("UNKNOWN_STRATEGY", ""):
        return raw
    if symbol.startswith("NG"):
        return "NG_CONSERVATIVE_BREAKOUT_M1"
    if symbol.startswith("BR"):
        return "BR_CONSERVATIVE_BREAKOUT"
    if symbol.startswith("USDRUB"):
        return "USD_INTRADAY_REGIME"
    return raw or "UNKNOWN_STRATEGY"


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser()
    p.add_argument("--symbol", default=os.getenv("SYMBOL"))
    p.add_argument("--symbols", default=os.getenv("SYMBOLS"))
    p.add_argument("--symbol-pattern", default=os.getenv("SYMBOL_PATTERN"))
    p.add_argument("--from-ts", default=os.getenv("FROM_TS"))
    p.add_argument("--to-ts", default=os.getenv("TO_TS"))
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--apply", action="store_true")
    p.add_argument("--replace", action="store_true")
    return p.parse_args()


def load_symbols(conn, args: argparse.Namespace) -> list[str]:
    # Русский комментарий: явный --symbol имеет приоритет над SYMBOLS из окружения.
    if args.symbol:
        return [args.symbol.strip()]
    if args.symbols:
        return [x.strip() for x in args.symbols.split(",") if x.strip()]

    if args.symbol_pattern:
        rows = conn.execute(
            """
            SELECT DISTINCT symbol
            FROM fills
            WHERE symbol ~ %s
            ORDER BY symbol
            """,
            (args.symbol_pattern,),
        ).fetchall()
        return [r["symbol"] for r in rows]

    rows = conn.execute("SELECT DISTINCT symbol FROM fills ORDER BY symbol").fetchall()
    return [r["symbol"] for r in rows]


def load_fills(conn, symbol: str, args: argparse.Namespace) -> list[dict]:
    params = [symbol]
    where = ["f.symbol = %s", "f.qty > 0", "f.price > 0"]

    if args.from_ts:
        where.append("f.ts >= %s")
        params.append(args.from_ts)
    if args.to_ts:
        where.append("f.ts < %s")
        params.append(args.to_ts)

    sql = f"""
        SELECT
            f.fill_id,
            f.ts,
            f.symbol,
            f.side,
            f.qty,
            f.price,
            COALESCE(f.commission, 0) AS commission,
            sf.signal_id,
            sf.side AS signal_side
        FROM fills f
        LEFT JOIN signal_fills sf ON sf.fill_id = f.fill_id
        WHERE {' AND '.join(where)}
        ORDER BY f.ts, f.fill_id
    """
    return list(conn.execute(sql, tuple(params)).fetchall())


def reconstruct(symbol: str, fills: list[dict]) -> list[dict]:
    open_longs = deque()
    open_shorts = deque()
    closed = []
    exit_batch_counter: dict[str, int] = {}

    for f in fills:
        fill_id = str(f["fill_id"])
        side = str(f["side"]).upper()
        qty = float(f["qty"] or 0.0)
        price = float(f["price"] or 0.0)
        ts = f["ts"]
        signal_id = f.get("signal_id")

        if side == "BUY":
            remaining = qty

            while remaining > 0 and open_shorts:
                s = open_shorts[0]
                matched = min(remaining, s["qty"])
                pnl = (s["price"] - price) * matched
                trade = build_trade(symbol, "SHORT", matched, s, f, pnl)
                batch_key = str(f.get("fill_id"))
                exit_batch_counter[batch_key] = exit_batch_counter.get(batch_key, 0) + 1
                trade["raw"]["exit_batch_key"] = batch_key
                trade["raw"]["exit_batch_trade_index"] = exit_batch_counter[batch_key]
                trade["raw"]["exit_batch_total_qty"] = float(qty)
                closed.append(trade)
                s["qty"] -= matched
                remaining -= matched
                if s["qty"] <= 1e-12:
                    open_shorts.popleft()

            if remaining > 1e-12:
                open_longs.append({
                    "qty": remaining,
                    "price": price,
                    "ts": ts,
                    "fill_id": fill_id,
                    "signal_id": signal_id,
                })

        elif side == "SELL":
            remaining = qty

            while remaining > 0 and open_longs:
                b = open_longs[0]
                matched = min(remaining, b["qty"])
                pnl = (price - b["price"]) * matched
                trade = build_trade(symbol, "LONG", matched, b, f, pnl)
                batch_key = str(f.get("fill_id"))
                exit_batch_counter[batch_key] = exit_batch_counter.get(batch_key, 0) + 1
                trade["raw"]["exit_batch_key"] = batch_key
                trade["raw"]["exit_batch_trade_index"] = exit_batch_counter[batch_key]
                trade["raw"]["exit_batch_total_qty"] = float(qty)
                closed.append(trade)
                b["qty"] -= matched
                remaining -= matched
                if b["qty"] <= 1e-12:
                    open_longs.popleft()

            if remaining > 1e-12:
                open_shorts.append({
                    "qty": remaining,
                    "price": price,
                    "ts": ts,
                    "fill_id": fill_id,
                    "signal_id": signal_id,
                })

    batch_sizes: dict[str, int] = {}
    for t in closed:
        key = str(t["raw"].get("exit_batch_key") or "")
        if key:
            batch_sizes[key] = batch_sizes.get(key, 0) + 1

    for t in closed:
        key = str(t["raw"].get("exit_batch_key") or "")
        batch_size = batch_sizes.get(key, 1)
        t["raw"]["exit_batch_size"] = batch_size
        t["raw"]["exit_batch_is_batch"] = bool(batch_size > 1)

    return closed


def build_trade(symbol: str, trade_side: str, qty: float, entry: dict, exit_fill: dict, pnl: float) -> dict:
    exit_ts = exit_fill["ts"]
    exit_msk = exit_ts.astimezone(MSK)
    strategy = norm_strategy(symbol, None)

    entry_signal_id = entry.get("signal_id")
    exit_signal_id = exit_fill.get("signal_id")

    trade_id = (
        f"{symbol}|{trade_side}|{entry.get('fill_id')}|"
        f"{exit_fill.get('fill_id')}|{qty:.8f}"
    )

    return {
        "trade_id": trade_id,
        "symbol": symbol,
        "strategy": strategy,
        "side": trade_side,
        "qty": qty,
        "entry_ts": entry["ts"],
        "exit_ts": exit_ts,
        "entry_price": float(entry["price"]),
        "exit_price": float(exit_fill["price"]),
        "pnl_points": float(pnl),
        "entry_fill_id": entry.get("fill_id"),
        "exit_fill_id": exit_fill.get("fill_id"),
        "entry_signal_id": entry_signal_id,
        "exit_signal_id": exit_signal_id,
        "exit_reason": None,
        "hour_msk": exit_msk.hour,
        "weekday": exit_msk.strftime("%A"),
        "session": session_ru(exit_msk.hour),
        "source": "materialize_closed_trades_from_fills_v1",
        "raw": {
            "exit_side": exit_fill.get("side"),
            "exit_signal_side": exit_fill.get("signal_side"),
        },
    }


def upsert_trades(conn, trades: list[dict]) -> int:
    n = 0
    for t in trades:
        conn.execute(
            """
            INSERT INTO analytics_closed_trades_v1 (
                trade_id, symbol, strategy, side, qty,
                entry_ts, exit_ts, entry_price, exit_price, pnl_points,
                entry_fill_id, exit_fill_id, entry_signal_id, exit_signal_id,
                exit_reason, hour_msk, weekday, session, source, raw,
                created_at, updated_at
            )
            VALUES (
                %(trade_id)s, %(symbol)s, %(strategy)s, %(side)s, %(qty)s,
                %(entry_ts)s, %(exit_ts)s, %(entry_price)s, %(exit_price)s, %(pnl_points)s,
                %(entry_fill_id)s, %(exit_fill_id)s, %(entry_signal_id)s, %(exit_signal_id)s,
                %(exit_reason)s, %(hour_msk)s, %(weekday)s, %(session)s, %(source)s, %(raw)s,
                now(), now()
            )
            ON CONFLICT (trade_id) DO UPDATE SET
                strategy = EXCLUDED.strategy,
                pnl_points = EXCLUDED.pnl_points,
                exit_reason = EXCLUDED.exit_reason,
                raw = EXCLUDED.raw,
                updated_at = now()
            """,
            {**t, "raw": Jsonb(t["raw"])},
        )
        n += 1
    return n


def main() -> int:
    args = parse_args()
    db = os.getenv("DATABASE_URL")
    if not db:
        raise SystemExit("DATABASE_URL is required")

    if not args.apply and not args.dry_run:
        args.dry_run = True

    with psycopg.connect(db, row_factory=dict_row) as conn:
        conn.execute(DDL)

        symbols = load_symbols(conn, args)
        total_trades = 0

        print("=== MATERIALIZE CLOSED TRADES FROM FILLS V1 ===")
        print(f"mode={'APPLY' if args.apply else 'DRY_RUN'}")
        print(f"symbols={','.join(symbols)}")
        print(f"from_ts={args.from_ts}")
        print(f"to_ts={args.to_ts}")
        print()

        for symbol in symbols:
            fills = load_fills(conn, symbol, args)
            trades = reconstruct(symbol, fills)
            total_trades += len(trades)

            print(
                f"SYMBOL_SUMMARY symbol={symbol} fills={len(fills)} "
                f"closed_trades={len(trades)}"
            )

            if args.apply:
                if args.replace:
                    conn.execute(
                        "DELETE FROM analytics_closed_trades_v1 WHERE symbol = %s",
                        (symbol,),
                    )
                written = upsert_trades(conn, trades)
                print(f"SYMBOL_APPLIED symbol={symbol} written={written}")

        if args.apply:
            conn.commit()

    print()
    print(f"TOTAL_CLOSED_TRADES={total_trades}")
    print(f"VERDICT={'APPLIED' if args.apply else 'DRY_RUN_ONLY'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
