from __future__ import annotations

import argparse
import subprocess
import sys
import time

import psycopg

from finam_core.analytics.statistics_repository import build_psycopg_url


def load_watch_symbols() -> list[str]:
    with psycopg.connect(build_psycopg_url()) as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT symbol
                FROM market_data_watch_universe
                WHERE is_enabled = true
                ORDER BY asset_group, symbol
            """)
            rows = [str(r[0]) for r in cur.fetchall()]
    return rows

def run_backfill(symbol: str, timeframe: str, lookback_hours: int, step_timeout_sec: int) -> bool:
    cmd = [
        sys.executable,
        "src/scripts/ingestion/backfill_finam_futures_market_bars.py",
        "--symbols", symbol,
        "--timeframe", timeframe,
        "--lookback-hours", str(lookback_hours),
    ]

    print("MARKET_BARS_INGESTION_STEP_START", " ".join(cmd), flush=True)
    try:
        result = subprocess.run(cmd, timeout=step_timeout_sec)
    except subprocess.TimeoutExpired:
        print(
            "MARKET_BARS_INGESTION_STEP_TIMEOUT "
            f"symbol={symbol} timeframe={timeframe} timeout_sec={step_timeout_sec}",
            flush=True,
        )
        return False
    ok = result.returncode == 0
    print(
        "MARKET_BARS_INGESTION_STEP_DONE "
        f"ok={ok} code={result.returncode} symbol={symbol} timeframe={timeframe}",
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

    requested_symbols = [x.strip() for x in args.symbols.split(",") if x.strip()]
    timeframes = [x.strip() for x in args.timeframes.split(",") if x.strip()]
    cycle = 0

    while True:
        cycle += 1
        print(f"MARKET_BARS_INGESTION_CYCLE_START cycle={cycle}", flush=True)

        # Reload the universe every cycle: the scout can add or disable instruments
        # without requiring a service restart.
        symbols = requested_symbols or load_watch_symbols()
        ok_all = True
        for tf in timeframes:
            for symbol in symbols:
                # One unavailable vendor code must not hold the remaining active
                # instruments hostage.  Each instrument is an independent update.
                ok_all = (
                    run_backfill(symbol, tf, args.lookback_hours, args.step_timeout_sec)
                    and ok_all
                )

        print(f"MARKET_BARS_INGESTION_CYCLE_DONE cycle={cycle} ok={ok_all}", flush=True)

        if args.once:
            return 0 if ok_all else 1

        time.sleep(max(10, args.interval_sec))


if __name__ == "__main__":
    raise SystemExit(main())
