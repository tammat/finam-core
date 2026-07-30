from __future__ import annotations

import argparse
import subprocess
import sys
import time

import psycopg

from finam_core.analytics.statistics_repository import build_psycopg_url


V5_FRESHNESS_PRIORITY = (
    "BRQ6@RTSX",
    "NGQ6@RTSX",
    "SBER@MISX",
    "GAZP@MISX",
    "LKOH@MISX",
    "NVTK@MISX",
    "VTBR@MISX",
)


def load_watch_targets() -> list[tuple[str, str]]:
    with psycopg.connect(build_psycopg_url()) as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT symbol, timeframe
                FROM market_data_watch_universe
                WHERE is_enabled = true
                ORDER BY
                    array_position(%s::text[], symbol) NULLS LAST,
                    asset_group,
                    symbol,
                    timeframe
            """, (list(V5_FRESHNESS_PRIORITY),))
            rows = [(str(r[0]), str(r[1])) for r in cur.fetchall()]
    return rows


def valid_finam_symbol(symbol: str) -> bool:
    # Finam's bars endpoint requires an explicit MIC.  Remediation-only
    # placeholders such as BTCUSD must not consume the retry budget of the
    # time-sensitive V5 market-data cycle.
    ticker, separator, mic = symbol.partition("@")
    return bool(ticker and separator and mic)


def parse_target_specs(value: str) -> list[tuple[str, str]]:
    targets: list[tuple[str, str]] = []
    for raw in value.split(","):
        item = raw.strip()
        if not item:
            continue
        symbol, separator, timeframe = item.rpartition("=")
        symbol, timeframe = symbol.strip(), timeframe.strip().upper()
        if not separator or not symbol or timeframe not in {"M1", "M5", "M15", "H1", "H4", "D1"}:
            raise ValueError(f"MARKET_BARS_TARGET_INVALID:{item}")
        targets.append((symbol, timeframe))
    return targets


def target_is_fresh(symbol: str, timeframe: str) -> bool:
    """A vendor timeout is degraded success when the target is already fresh."""
    freshness_minutes = {"M1": 5, "M5": 15, "M15": 45, "H1": 180, "H4": 720, "D1": 2880}
    limit = freshness_minutes.get(timeframe.upper(), 15)
    try:
        with psycopg.connect(build_psycopg_url()) as conn:
            row = conn.execute(
                """
                SELECT max(ts) >= clock_timestamp()-(%s * interval '1 minute')
                FROM market_bars WHERE symbol=%s AND timeframe=%s
                """,
                (limit, symbol, timeframe),
            ).fetchone()
        return bool(row and row[0])
    except Exception as exc:
        print(
            f"MARKET_BARS_FRESHNESS_CHECK_FAILED symbol={symbol} timeframe={timeframe} "
            f"error={type(exc).__name__}:{exc}",
            flush=True,
        )
        return False

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
        fresh = target_is_fresh(symbol, timeframe)
        print(
            "MARKET_BARS_INGESTION_STEP_TIMEOUT "
            f"symbol={symbol} timeframe={timeframe} timeout_sec={step_timeout_sec} "
            f"already_fresh={fresh}",
            flush=True,
        )
        return fresh
    ok = result.returncode == 0
    if not ok and target_is_fresh(symbol, timeframe):
        print(
            "MARKET_BARS_INGESTION_STEP_DEGRADED_ALREADY_FRESH "
            f"symbol={symbol} timeframe={timeframe} code={result.returncode}",
            flush=True,
        )
        return True
    print(
        "MARKET_BARS_INGESTION_STEP_DONE "
        f"ok={ok} code={result.returncode} symbol={symbol} timeframe={timeframe}",
        flush=True,
    )
    return ok


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--symbols", default="")
    parser.add_argument("--targets", default="")
    parser.add_argument("--timeframes", default="M1,M5,H1")
    parser.add_argument("--lookback-hours", type=int, default=2)
    parser.add_argument("--interval-sec", type=int, default=60)
    parser.add_argument("--once", action="store_true")
    parser.add_argument("--step-timeout-sec", type=int, default=180)
    args = parser.parse_args()

    requested_symbols = [x.strip() for x in args.symbols.split(",") if x.strip()]
    requested_targets = parse_target_specs(args.targets)
    if requested_symbols and requested_targets:
        parser.error("--symbols and --targets are mutually exclusive")
    timeframes = [x.strip() for x in args.timeframes.split(",") if x.strip()]
    cycle = 0

    while True:
        cycle += 1
        print(f"MARKET_BARS_INGESTION_CYCLE_START cycle={cycle}", flush=True)

        # Reload the universe every cycle: the scout can add or disable instruments
        # without requiring a service restart.
        targets = (
            requested_targets
            or ([(symbol, timeframe) for timeframe in timeframes for symbol in requested_symbols]
                if requested_symbols else load_watch_targets())
        )
        ok_all = True
        for symbol, timeframe in targets:
            if not valid_finam_symbol(symbol):
                print(
                    "MARKET_BARS_INGESTION_TARGET_SKIPPED "
                    f"symbol={symbol} timeframe={timeframe} reason=MISSING_MIC",
                    flush=True,
                )
                ok_all = False
                continue
            # One unavailable vendor code must not hold the remaining active
            # instruments hostage.  Each instrument is an independent update.
            ok_all = (
                run_backfill(symbol, timeframe, args.lookback_hours, args.step_timeout_sec)
                and ok_all
            )

        print(f"MARKET_BARS_INGESTION_CYCLE_DONE cycle={cycle} ok={ok_all}", flush=True)

        if args.once:
            return 0 if ok_all else 1

        time.sleep(max(10, args.interval_sec))


if __name__ == "__main__":
    raise SystemExit(main())
