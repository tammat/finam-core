#!/usr/bin/env python3
from __future__ import annotations

import os
from datetime import datetime, timezone
import psycopg


SYMBOL = os.getenv("EQUITY_SYMBOL", "SBER@MISX")
TIMEFRAME = os.getenv("EQUITY_TIMEFRAME", "M5")
ACTIVE_SINCE_UTC = os.getenv("ACTIVE_SINCE_UTC", "2026-06-19 05:55:21+00")


def env_flag(name: str) -> str:
    return os.getenv(name, "0")


def main() -> int:
    print("=== EQUITY MTF CLOSED BAR ROUTE REACHABILITY V1.1 ===")
    print("mode=read_only")
    print(f"runtime_allow={env_flag('RUNTIME_ALLOW_TRADING')}")
    print(f"execution_enabled={env_flag('EXECUTION_ENABLED')}")
    print(f"real_trading_enabled={env_flag('REAL_TRADING_ENABLED')}")
    print("db_update=0")
    print(f"symbol={SYMBOL}")
    print(f"timeframe={TIMEFRAME}")
    print(f"active_since_utc={ACTIVE_SINCE_UTC}")

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
            print("EQUITY_MTF_RESTART_AWARE_RUNTIME_ROWS")
            for row in runtime_rows:
                print(
                    "EQUITY_MTF_RESTART_AWARE_RUNTIME_ROW "
                    f"symbol={row[0]} strategy={row[1]} timeframe={row[2]} "
                    f"is_enabled={int(bool(row[3]))} score={row[4]} "
                    f"source={row[5]} updated_at={row[6]}"
                )

            cur.execute(
                """
                select
                    count(*)::int,
                    min(ts),
                    max(ts)
                from market_bars
                where symbol = %s
                  and timeframe = %s
                  and ts >= %s::timestamptz
                """,
                (SYMBOL, TIMEFRAME, ACTIVE_SINCE_UTC),
            )
            bars_after_restart, first_bar_after_restart, last_bar_after_restart = cur.fetchone()

            print()
            print("EQUITY_MTF_RESTART_AWARE_BAR_ROWS")
            print(
                "EQUITY_MTF_RESTART_AWARE_BAR_ROW "
                f"symbol={SYMBOL} timeframe={TIMEFRAME} "
                f"bars_after_restart={bars_after_restart} "
                f"first_ts={first_bar_after_restart} last_ts={last_bar_after_restart}"
            )

            cur.execute(
                """
                select ts, open, high, low, close, volume
                from market_bars
                where symbol = %s
                  and timeframe = %s
                  and ts >= %s::timestamptz
                order by ts desc
                limit 10
                """,
                (SYMBOL, TIMEFRAME, ACTIVE_SINCE_UTC),
            )
            rows = cur.fetchall()

            print()
            print("EQUITY_MTF_RESTART_AWARE_LATEST_BAR_ROWS")
            for ts, open_, high, low, close, volume in rows:
                print(
                    "EQUITY_MTF_RESTART_AWARE_LATEST_BAR_ROW "
                    f"ts={ts} open={open_} high={high} low={low} close={close} volume={volume}"
                )

            cur.execute(
                """
                select
                    strategy,
                    block_reason,
                    count(*)::int,
                    min(ts),
                    max(ts)
                from runtime_guard_pre_signal_block_audit_v1
                where symbol = %s
                  and ts >= %s::timestamptz
                group by strategy, block_reason
                order by count(*) desc, strategy, block_reason
                """,
                (SYMBOL, ACTIVE_SINCE_UTC),
            )
            guard_rows = cur.fetchall()

            print()
            print("EQUITY_MTF_RESTART_AWARE_GUARD_ROWS")
            for strategy, reason, rows_count, first_ts, last_ts in guard_rows:
                print(
                    "EQUITY_MTF_RESTART_AWARE_GUARD_ROW "
                    f"strategy={strategy} reason={reason} rows={rows_count} "
                    f"first_ts={first_ts} last_ts={last_ts}"
                )

            cur.execute(
                """
                select
                    strategy,
                    status,
                    count(*)::int,
                    min(created_at),
                    max(created_at)
                from signals
                where symbol = %s
                  and created_at >= %s::timestamptz
                group by strategy, status
                order by count(*) desc, strategy, status
                """,
                (SYMBOL, ACTIVE_SINCE_UTC),
            )
            signal_rows = cur.fetchall()

            print()
            print("EQUITY_MTF_RESTART_AWARE_SIGNAL_ROWS")
            for strategy, status, rows_count, first_ts, last_ts in signal_rows:
                print(
                    "EQUITY_MTF_RESTART_AWARE_SIGNAL_ROW "
                    f"strategy={strategy} status={status} rows={rows_count} "
                    f"first_ts={first_ts} last_ts={last_ts}"
                )

    runtime_ok = int(any(bool(r[3]) for r in runtime_rows))
    bars_after_restart_ok = int((bars_after_restart or 0) > 0)
    guard_after_restart = sum(int(r[2] or 0) for r in guard_rows)
    signals_after_restart = sum(int(r[2] or 0) for r in signal_rows)

    print()
    print("EQUITY_MTF_CLOSED_BAR_ROUTE_REACHABILITY_V1_1_SUMMARY")
    print(f"runtime_ok={runtime_ok}")
    print(f"bars_after_restart={bars_after_restart or 0}")
    print(f"bars_after_restart_ok={bars_after_restart_ok}")
    print(f"guard_after_restart={guard_after_restart}")
    print(f"signals_after_restart={signals_after_restart}")
    print("db_update=0")
    print("runtime_changes_required=0")
    print("execution_changes_required=0")
    print(f"real_trading_enabled={env_flag('REAL_TRADING_ENABLED')}")
    print(f"execution_enabled={env_flag('EXECUTION_ENABLED')}")

    if runtime_ok and bars_after_restart_ok and guard_after_restart == 0 and signals_after_restart == 0:
        print("VERDICT=EQUITY_BARS_AFTER_RESTART_BUT_HANDLER_NOT_REACHED")
    elif runtime_ok and bars_after_restart_ok and guard_after_restart > 0 and signals_after_restart == 0:
        print("VERDICT=EQUITY_HANDLER_REACHED_GUARD_BLOCKED_AFTER_RESTART")
    elif runtime_ok and bars_after_restart_ok and signals_after_restart > 0:
        print("VERDICT=EQUITY_SIGNAL_REACHED_AFTER_RESTART")
    elif runtime_ok and not bars_after_restart_ok:
        print("VERDICT=EQUITY_NO_BARS_AFTER_RESTART")
    else:
        print("VERDICT=EQUITY_RESTART_AWARE_REACHABILITY_REVIEW_REQUIRED")

    print("EQUITY_MTF_CLOSED_BAR_ROUTE_REACHABILITY_V1_1_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
