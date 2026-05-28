from __future__ import annotations

import argparse
import os
import subprocess
import sys
from datetime import date

import psycopg
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb

from finam_core.analytics.statistics_repository import build_psycopg_url


def migrate(conn):
    with conn.cursor() as cur:
        cur.execute("""
        CREATE TABLE IF NOT EXISTS historical_signal_replay_runs (
            id bigserial PRIMARY KEY,
            run_id text NOT NULL UNIQUE,
            symbol text NOT NULL,
            strategy text NOT NULL,
            timeframe text NOT NULL,
            date_from date NOT NULL,
            date_to date NOT NULL,
            created_at timestamptz NOT NULL DEFAULT now()
        );
        """)


def load_bars(conn, symbol: str, timeframe: str, date_from: date, date_to: date):
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute("""
        SELECT ts, symbol, timeframe, open, high, low, close, volume
        FROM market_bars
        WHERE symbol = %s
          AND timeframe = %s
          AND (ts AT TIME ZONE 'Europe/Moscow')::date BETWEEN %s AND %s
        ORDER BY ts
        """, (symbol, timeframe, date_from, date_to))
        return [dict(r) for r in cur.fetchall()]


def insert_trade(conn, *, ts, symbol, side, qty, price, strategy, timeframe, run_id, reason):
    fill_id = f"hist_replay:{run_id}:{symbol}:{timeframe}:{ts.isoformat()}:{side}"
    with conn.cursor() as cur:
        cur.execute("""
        INSERT INTO trades (
            ts, symbol, side, qty, price,
            fill_id, origin, trade_source,
            is_invalid, invalid_reason,
            strategy, timeframe, payload
        )
        VALUES (
            %(ts)s, %(symbol)s, %(side)s, %(qty)s, %(price)s,
            %(fill_id)s, 'historical_signal_replay', 'paper',
            false, '',
            %(strategy)s, %(timeframe)s, %(payload)s
        )
        ON CONFLICT (fill_id) DO NOTHING
        """, {
            "ts": ts,
            "symbol": symbol,
            "side": side,
            "qty": qty,
            "price": price,
            "fill_id": fill_id,
            "strategy": strategy,
            "timeframe": timeframe,
            "payload": Jsonb({
                "run_id": run_id,
                "reason": reason,
                "paper_only": True,
                "historical_replay": True,
            }),
        })


def run_simple_breakout_replay(conn, *, bars, symbol: str, strategy: str, timeframe: str, run_id: str):
    """
    Русский комментарий:
    V1 intentionally simple.
    Логика:
    - если close пробивает максимум последних N баров → BUY;
    - выход через hold_n баров → SELL;
    - только одна позиция одновременно.
    """
    lookback = 12
    hold_n = 6
    qty = 1.0

    in_position = False
    entry_index = -1
    inserted = 0

    for i in range(lookback, len(bars)):
        bar = bars[i]
        prev = bars[i - lookback:i]
        prev_high = max(float(x["high"]) for x in prev)

        close = float(bar["close"])

        if not in_position and close > prev_high:
            insert_trade(
                conn,
                ts=bar["ts"],
                symbol=symbol,
                side="BUY",
                qty=qty,
                price=close,
                strategy=strategy,
                timeframe=timeframe,
                run_id=run_id,
                reason="historical_breakout_buy",
            )
            in_position = True
            entry_index = i
            inserted += 1
            continue

        if in_position and i - entry_index >= hold_n:
            insert_trade(
                conn,
                ts=bar["ts"],
                symbol=symbol,
                side="SELL",
                qty=qty,
                price=close,
                strategy=strategy,
                timeframe=timeframe,
                run_id=run_id,
                reason="historical_time_exit",
            )
            in_position = False
            entry_index = -1
            inserted += 1

    return inserted


def run_research_for_dates(py: str, date_from: date, date_to: date) -> int:
    current = date_from
    failed = 0

    while current <= date_to:
        cmds = [
            [py, "src/scripts/analytics/build_intraday_pnl.py", "--date", current.isoformat(), "--migrate", "--save"],
            [py, "src/scripts/analytics/build_regime_snapshots_v2.py", "--date", current.isoformat(), "--migrate", "--save"],
            [py, "src/scripts/analytics/build_trade_context_envelopes.py", "--date", current.isoformat(), "--migrate", "--save"],
            [py, "src/scripts/analytics/build_regime_aware_edge_v1.py", "--date", current.isoformat(), "--migrate", "--save"],
            [py, "src/scripts/analytics/build_edge_validation_table.py", "--date", current.isoformat(), "--migrate", "--save"],
        ]

        for cmd in cmds:
            print("HISTORICAL_SIGNAL_REPLAY_RESEARCH_CMD " + " ".join(cmd), flush=True)
            rc = subprocess.run(cmd).returncode
            if rc != 0:
                failed += 1
                print(f"HISTORICAL_SIGNAL_REPLAY_RESEARCH_FAILED date={current} rc={rc}", flush=True)
                break

        current = date.fromordinal(current.toordinal() + 1)

    return failed


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--symbol", required=True)
    parser.add_argument("--timeframe", default="M5")
    parser.add_argument("--from-date", required=True)
    parser.add_argument("--to-date", required=True)
    parser.add_argument("--strategy", default="HISTORICAL_BREAKOUT_V1")
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--research", action="store_true")
    args = parser.parse_args()

    date_from = date.fromisoformat(args.from_date)
    date_to = date.fromisoformat(args.to_date)
    database_url = os.getenv("DATABASE_URL") or build_psycopg_url()

    with psycopg.connect(database_url) as conn:
        migrate(conn)

        with conn.cursor() as cur:
            cur.execute("""
            INSERT INTO historical_signal_replay_runs (
                run_id, symbol, strategy, timeframe, date_from, date_to
            )
            VALUES (%s,%s,%s,%s,%s,%s)
            ON CONFLICT (run_id) DO NOTHING
            """, (args.run_id, args.symbol, args.strategy, args.timeframe, date_from, date_to))

        bars = load_bars(conn, args.symbol, args.timeframe, date_from, date_to)

        inserted = run_simple_breakout_replay(
            conn,
            bars=bars,
            symbol=args.symbol,
            strategy=args.strategy,
            timeframe=args.timeframe,
            run_id=args.run_id,
        )

        conn.commit()

    print(
        f"HISTORICAL_SIGNAL_REPLAY_OK run_id={args.run_id} symbol={args.symbol} "
        f"bars={len(bars)} synthetic_trades={inserted}",
        flush=True,
    )

    if args.research:
        failed = run_research_for_dates(sys.executable, date_from, date_to)
        if failed:
            return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
