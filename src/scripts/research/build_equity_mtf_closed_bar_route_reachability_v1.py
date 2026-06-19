#!/usr/bin/env python3
from __future__ import annotations

import os
from datetime import datetime, timezone
import psycopg


SYMBOL = os.getenv("EQUITY_SYMBOL", "SBER@MISX")
TIMEFRAME = os.getenv("EQUITY_TIMEFRAME", "M5")
LOOKBACK_MINUTES = int(os.getenv("LOOKBACK_MINUTES", "240"))


def env_flag(name: str) -> str:
    return os.getenv(name, "0")


def main() -> int:
    print("=== EQUITY MTF CLOSED BAR ROUTE REACHABILITY V1 ===")
    print("mode=read_only")
    print(f"runtime_allow={env_flag('RUNTIME_ALLOW_TRADING')}")
    print(f"execution_enabled={env_flag('EXECUTION_ENABLED')}")
    print(f"real_trading_enabled={env_flag('REAL_TRADING_ENABLED')}")
    print("db_update=0")
    print(f"symbol={SYMBOL}")
    print(f"timeframe={TIMEFRAME}")
    print(f"lookback_minutes={LOOKBACK_MINUTES}")

    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        print("VERDICT=NO_DATABASE_URL")
        return 2

    with psycopg.connect(database_url) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                select symbol, strategy, timeframe, is_enabled, score, source, updated_at
                from runtime_active_universe
                where symbol = %s
                order by updated_at desc nulls last
                limit 5
                """,
                (SYMBOL,),
            )
            runtime_rows = cur.fetchall()

            print()
            print("EQUITY_MTF_RUNTIME_ROWS")
            for row in runtime_rows:
                print(
                    "EQUITY_MTF_RUNTIME_ROW "
                    f"symbol={row[0]} strategy={row[1]} timeframe={row[2]} "
                    f"is_enabled={int(bool(row[3]))} score={row[4]} source={row[5]} updated_at={row[6]}"
                )

            cur.execute(
                """
                select
                    count(*)::int as bars_total,
                    count(*) filter (where ts >= now() - (%s::text || ' minutes')::interval)::int as fresh_bars,
                    min(ts),
                    max(ts)
                from market_bars
                where symbol = %s
                  and timeframe = %s
                """,
                (LOOKBACK_MINUTES, SYMBOL, TIMEFRAME),
            )
            bars_total, fresh_bars, first_ts, last_ts = cur.fetchone()

            print()
            print("EQUITY_MTF_BAR_SUMMARY_ROWS")
            print(
                "EQUITY_MTF_BAR_SUMMARY_ROW "
                f"symbol={SYMBOL} timeframe={TIMEFRAME} "
                f"bars_total={bars_total} fresh_bars={fresh_bars} "
                f"first_ts={first_ts} last_ts={last_ts}"
            )

            cur.execute(
                """
                select ts, open, high, low, close, volume
                from market_bars
                where symbol = %s
                  and timeframe = %s
                order by ts desc
                limit 10
                """,
                (SYMBOL, TIMEFRAME),
            )
            rows = cur.fetchall()

            print()
            print("EQUITY_MTF_LATEST_BAR_ROWS")
            for ts, open_, high, low, close, volume in rows:
                print(
                    "EQUITY_MTF_LATEST_BAR_ROW "
                    f"ts={ts} open={open_} high={high} low={low} close={close} volume={volume}"
                )

            cur.execute(
                """
                select
                    count(*)::int,
                    min(ts),
                    max(ts)
                from runtime_guard_pre_signal_block_audit_v1
                where symbol = %s
                  and ts >= now() - (%s::text || ' minutes')::interval
                """,
                (SYMBOL, LOOKBACK_MINUTES),
            )
            guard_rows, guard_first, guard_last = cur.fetchone()

            print()
            print("EQUITY_MTF_GUARD_REACHABILITY_ROWS")
            print(
                "EQUITY_MTF_GUARD_REACHABILITY_ROW "
                f"fresh_guard_rows={guard_rows} first_ts={guard_first} last_ts={guard_last}"
            )

            cur.execute(
                """
                select
                    count(*)::int,
                    min(created_at),
                    max(created_at)
                from signals
                where symbol = %s
                  and created_at >= now() - (%s::text || ' minutes')::interval
                """,
                (SYMBOL, LOOKBACK_MINUTES),
            )
            signal_rows, signal_first, signal_last = cur.fetchone()

            print()
            print("EQUITY_MTF_SIGNAL_REACHABILITY_ROWS")
            print(
                "EQUITY_MTF_SIGNAL_REACHABILITY_ROW "
                f"fresh_signal_rows={signal_rows} first_ts={signal_first} last_ts={signal_last}"
            )

    runtime_ok = int(any(bool(r[3]) for r in runtime_rows))
    bars_ok = int((bars_total or 0) > 0)
    fresh_bars_ok = int((fresh_bars or 0) > 0)
    guard_or_signal = int((guard_rows or 0) > 0 or (signal_rows or 0) > 0)

    print()
    print("EQUITY_MTF_CLOSED_BAR_ROUTE_REACHABILITY_SUMMARY")
    print(f"runtime_ok={runtime_ok}")
    print(f"bars_ok={bars_ok}")
    print(f"fresh_bars_ok={fresh_bars_ok}")
    print(f"fresh_guard_or_signal_rows={guard_or_signal}")
    print("db_update=0")
    print("runtime_changes_required=0")
    print("execution_changes_required=0")
    print(f"real_trading_enabled={env_flag('REAL_TRADING_ENABLED')}")
    print(f"execution_enabled={env_flag('EXECUTION_ENABLED')}")

    if runtime_ok and bars_ok and fresh_bars_ok and not guard_or_signal:
        print("VERDICT=EQUITY_BARS_FRESH_BUT_RUNTIME_HANDLER_NOT_REACHED")
    elif runtime_ok and bars_ok and not fresh_bars_ok:
        print("VERDICT=EQUITY_BARS_STALE_AFTER_RESTART")
    elif runtime_ok and not bars_ok:
        print("VERDICT=EQUITY_RUNTIME_OK_NO_MARKET_BARS")
    elif guard_or_signal:
        print("VERDICT=EQUITY_HANDLER_OR_SIGNAL_REACHED")
    else:
        print("VERDICT=EQUITY_ROUTE_REACHABILITY_REVIEW_REQUIRED")

    print("EQUITY_MTF_CLOSED_BAR_ROUTE_REACHABILITY_V1_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
