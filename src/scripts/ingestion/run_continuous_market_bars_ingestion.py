from __future__ import annotations

import argparse
import subprocess
import sys
import time

import psycopg

from finam_core.analytics.statistics_repository import build_psycopg_url


def load_watch_symbols() -> str:
    with psycopg.connect(build_psycopg_url()) as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT symbol
                FROM market_data_watch_universe
                WHERE is_enabled = true
                ORDER BY asset_group, symbol
            """)
            rows = [str(r[0]) for r in cur.fetchall()]
    return ",".join(rows)

def run_backfill(symbols: str, timeframe: str, lookback_hours: int, step_timeout_sec: int) -> bool:
    cmd = [
        sys.executable,
        "src/scripts/ingestion/backfill_finam_futures_market_bars.py",
        "--symbols", symbols,
        "--timeframe", timeframe,
        "--lookback-hours", str(lookback_hours),
    ]

    print("MARKET_BARS_INGESTION_STEP_START", " ".join(cmd), flush=True)
    try:
        result = subprocess.run(cmd, timeout=step_timeout_sec)
    except subprocess.TimeoutExpired:
        print(
            f"MARKET_BARS_INGESTION_STEP_TIMEOUT timeframe={timeframe} timeout_sec={step_timeout_sec}",
            flush=True,
        )
        return False
    ok = result.returncode == 0
    print(
        f"MARKET_BARS_INGESTION_STEP_DONE ok={ok} code={result.returncode} timeframe={timeframe}",
        flush=True,
    )
    return ok


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--symbols", default="")
    parser.add_argument("--timeframes", default="M1,M5,H1")
    parser.add_argument("--lookback-hours", type=int, default=2)
    parser.add_argument("--interval-sec", type=int, default=60)
    parser.add_argument("--once", action="store_true")
    parser.add_argument("--step-timeout-sec", type=int, default=180)
    args = parser.parse_args()

    symbols = args.symbols.strip() or load_watch_symbols()
    timeframes = [x.strip() for x in args.timeframes.split(",") if x.strip()]
    cycle = 0

    while True:
        cycle += 1
        print(f"MARKET_BARS_INGESTION_CYCLE_START cycle={cycle}", flush=True)

        ok_all = True
        for tf in timeframes:
            ok_all = run_backfill(symbols, tf, args.lookback_hours, args.step_timeout_sec) and ok_all

        print(f"MARKET_BARS_INGESTION_CYCLE_DONE cycle={cycle} ok={ok_all}", flush=True)

        if args.once:
            return 0 if ok_all else 1

        time.sleep(max(10, args.interval_sec))


if __name__ == "__main__":
    raise SystemExit(main())
