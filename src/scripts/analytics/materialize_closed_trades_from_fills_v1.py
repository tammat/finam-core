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


DDL = "SELECT 1"  # Структура управляется только версионированными миграциями.


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
    if symbol.endswith("@MISX"):
        return "VWAP_BANDS_MR"
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
            sf.side AS signal_side,
            COALESCE(NULLIF(s.strategy,''),NULLIF(t.strategy,''),NULLIF(t.payload->>'strategy','')) AS signal_strategy,
            COALESCE(NULLIF(s.timeframe,''),NULLIF(t.timeframe,''),NULLIF(t.payload->>'timeframe','')) AS signal_timeframe,
            COALESCE(NULLIF(s.horizon,''),NULLIF(t.payload->>'horizon','')) AS signal_horizon,
            COALESCE(NULLIF(s.regime,''),NULLIF(t.payload->>'regime','')) AS signal_regime
        FROM fills f
        LEFT JOIN signal_fills sf ON sf.fill_id = f.fill_id
        LEFT JOIN LATERAL (
            SELECT strategy, timeframe, horizon, regime
            FROM signals
            WHERE signal_id = sf.signal_id
            ORDER BY ts DESC, id DESC
            LIMIT 1
        ) s ON true
        LEFT JOIN LATERAL (
            SELECT strategy, timeframe, payload
            FROM trades
            WHERE fill_id = f.fill_id
            ORDER BY ts DESC, id DESC
            LIMIT 1
        ) t ON true
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
                    "strategy": f.get("signal_strategy"),
                    "timeframe": f.get("signal_timeframe"),
                    "horizon": f.get("signal_horizon"),
                    "regime": f.get("signal_regime"),
                    "commission_per_unit": float(f.get("commission") or 0.0) / qty,
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
                    "strategy": f.get("signal_strategy"),
                    "timeframe": f.get("signal_timeframe"),
                    "horizon": f.get("signal_horizon"),
                    "regime": f.get("signal_regime"),
                    "commission_per_unit": float(f.get("commission") or 0.0) / qty,
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
    strategy = norm_strategy(symbol, entry.get("strategy"))

    entry_signal_id = entry.get("signal_id")
    exit_signal_id = exit_fill.get("signal_id")

    trade_id = (
        f"{symbol}|{trade_side}|{entry.get('fill_id')}|"
        f"{exit_fill.get('fill_id')}|{qty:.8f}"
    )
    entry_commission = float(entry.get("commission_per_unit") or 0.0) * qty
    exit_fill_qty = float(exit_fill.get("qty") or qty)
    exit_commission = float(exit_fill.get("commission") or 0.0) * qty / exit_fill_qty
    commission = entry_commission + exit_commission

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
        "commission": commission,
        "net_pnl": float(pnl) - commission,
        "entry_fill_id": entry.get("fill_id"),
        "exit_fill_id": exit_fill.get("fill_id"),
        "entry_signal_id": entry_signal_id,
        "exit_signal_id": exit_signal_id,
        "exit_reason": None,
        "timeframe": entry.get("timeframe") or "LIVE",
        "horizon": entry.get("horizon") or "INTRADAY",
        "regime": entry.get("regime") or "UNKNOWN",
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


def upsert_canonical_trades(conn, trades: list[dict], legacy_cutoff) -> int:
    """Записывает тот же факт закрытия в каноническую таблицу без дублей."""
    written = 0
    for t in trades:
        if legacy_cutoff is not None and t["exit_ts"] <= legacy_cutoff:
            continue
        result = conn.execute(
            """
            WITH claimed AS (
                INSERT INTO analytics.paper_closed_trade_identity_v2(
                    materialized_trade_id,entry_fill_id,exit_fill_id
                )
                SELECT %(trade_id)s,%(entry_fill_id)s,%(exit_fill_id)s
                WHERE NOT EXISTS (
                    SELECT 1 FROM closed_trades
                    WHERE payload->>'materialized_trade_id'=%(trade_id)s
                       OR (
                            payload->>'entry_fill_id'=%(entry_fill_id)s
                        AND payload->>'exit_fill_id'=%(exit_fill_id)s
                       )
                )
                ON CONFLICT(materialized_trade_id) DO NOTHING
                RETURNING materialized_trade_id
            )
            INSERT INTO closed_trades (
                signal_id, symbol, side, entry_ts, exit_ts, qty,
                entry_price, exit_price, gross_pnl, commission, net_pnl,
                horizon, strategy, regime, trade_source, payload,
                timeframe, source, opened_at, closed_at, holding_seconds
            )
            SELECT
                %(entry_signal_id)s, %(symbol)s, %(side)s, %(entry_ts)s, %(exit_ts)s, %(qty)s,
                %(entry_price)s, %(exit_price)s, %(pnl_points)s, %(commission)s, %(net_pnl)s,
                %(horizon)s, %(strategy)s, %(regime)s, 'paper', %(payload)s,
                %(timeframe)s, 'paper_fill_materializer_v2', %(entry_ts)s, %(exit_ts)s,
                greatest(0, extract(epoch FROM (%(exit_ts)s - %(entry_ts)s))::integer)
            WHERE EXISTS (SELECT 1 FROM claimed)
            RETURNING id
            """,
            {**t, "payload": Jsonb({
                "materialized_trade_id": t["trade_id"],
                "entry_fill_id": t["entry_fill_id"],
                "exit_fill_id": t["exit_fill_id"],
                "exit_signal_id": t["exit_signal_id"],
                "materializer": "paper_fill_materializer_v2",
            })},
        ).fetchone()
        written += int(result is not None)
    return written


def refresh_canonical_attribution(conn, trades: list[dict]) -> int:
    updated = 0
    for t in trades:
        result = conn.execute(
            """UPDATE closed_trades
               SET strategy=%(strategy)s,timeframe=%(timeframe)s,
                   horizon=%(horizon)s,regime=%(regime)s
               WHERE source='paper_fill_materializer_v2'
                 AND payload->>'materialized_trade_id'=%(trade_id)s
                 AND (strategy IS DISTINCT FROM %(strategy)s
                   OR timeframe IS DISTINCT FROM %(timeframe)s
                   OR horizon IS DISTINCT FROM %(horizon)s
                   OR regime IS DISTINCT FROM %(regime)s)""",
            t,
        )
        updated += result.rowcount
    return updated


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
        total_canonical_written = 0
        total_attribution_updated = 0
        legacy_cutoff = conn.execute(
            """SELECT max(exit_ts) FROM closed_trades
               WHERE source <> 'paper_fill_materializer_v2'"""
        ).fetchone()["max"]

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
                canonical_written = upsert_canonical_trades(conn, trades, legacy_cutoff)
                attribution_updated = refresh_canonical_attribution(conn, trades)
                total_canonical_written += canonical_written
                total_attribution_updated += attribution_updated
                print(
                    f"SYMBOL_APPLIED symbol={symbol} analytics_written={written} "
                    f"canonical_written={canonical_written} "
                    f"attribution_updated={attribution_updated}"
                )

        if args.apply:
            conn.commit()

    print()
    print(f"TOTAL_CLOSED_TRADES={total_trades}")
    print(f"CANONICAL_WRITTEN={total_canonical_written}")
    print(f"ATTRIBUTION_UPDATED={total_attribution_updated}")
    print(f"VERDICT={'APPLIED' if args.apply else 'DRY_RUN_ONLY'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
