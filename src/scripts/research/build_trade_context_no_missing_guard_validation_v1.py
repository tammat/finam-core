#!/usr/bin/env python3
from __future__ import annotations

import os
import psycopg2
from psycopg2.extras import RealDictCursor


RECENT_SQL = """
select
    created_at::date as trade_date,
    count(*) as trades,
    count(*) filter (where strategy is null or btrim(strategy) = '') as strategy_missing,
    count(*) filter (where timeframe is null or btrim(timeframe) = '') as timeframe_missing,
    count(*) filter (where continuous_symbol is null or btrim(continuous_symbol) = '') as continuous_symbol_missing,
    min(created_at) as first_trade,
    max(created_at) as last_trade
from trades
where created_at::date >= current_date - interval '3 days'
group by created_at::date
order by trade_date desc;
"""


TODAY_SQL = """
select
    count(*) as trades_today,
    count(*) filter (where strategy is null or btrim(strategy) = '') as strategy_missing_today,
    count(*) filter (where timeframe is null or btrim(timeframe) = '') as timeframe_missing_today,
    count(*) filter (where continuous_symbol is null or btrim(continuous_symbol) = '') as continuous_symbol_missing_today
from trades
where created_at::date = current_date;
"""


DISCOVERY_SQL = """
select
    count(*) as discovery_total,
    count(*) filter (where status = 'NEW') as discovery_new,
    count(*) filter (where status = 'TEST_CLOSED') as discovery_test_closed
from signal_strategy_discovery_events;
"""


MARKER_SQL = """
select
    count(*) as unresolved_new
from signal_strategy_discovery_events
where status = 'NEW';
"""


def main() -> int:
    dsn = os.getenv("DATABASE_URL", "dbname=finam_core user=postgres")

    print("=== TRADE CONTEXT NO MISSING GUARD VALIDATION V1 ===")
    print("mode=diagnostic")
    print("runtime_allow=0")
    print("execution_enabled=0")
    print("real_trading_enabled=0")

    failures = []

    with psycopg2.connect(dsn) as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(TODAY_SQL)
            today = cur.fetchone()

            print()
            print("TRADE_CONTEXT_TODAY_SUMMARY")
            for key, value in today.items():
                print(f"{key}={value}")

            if int(today["strategy_missing_today"] or 0) > 0:
                failures.append("STRATEGY_MISSING_TODAY")

            if int(today["timeframe_missing_today"] or 0) > 0:
                failures.append("TIMEFRAME_MISSING_TODAY")

            if int(today["continuous_symbol_missing_today"] or 0) > 0:
                failures.append("CONTINUOUS_SYMBOL_MISSING_TODAY")

            cur.execute(RECENT_SQL)
            rows = cur.fetchall()

            print()
            print("TRADE_CONTEXT_RECENT_ROWS")
            for row in rows:
                print(
                    "TRADE_CONTEXT_RECENT_ROW "
                    f"trade_date={row['trade_date']} "
                    f"trades={row['trades']} "
                    f"strategy_missing={row['strategy_missing']} "
                    f"timeframe_missing={row['timeframe_missing']} "
                    f"continuous_symbol_missing={row['continuous_symbol_missing']} "
                    f"first_trade={row['first_trade']} "
                    f"last_trade={row['last_trade']}"
                )

            cur.execute(DISCOVERY_SQL)
            discovery = cur.fetchone()

            print()
            print("SIGNAL_STRATEGY_DISCOVERY_SUMMARY")
            for key, value in discovery.items():
                print(f"{key}={value}")

            cur.execute(MARKER_SQL)
            unresolved = cur.fetchone()

            print()
            print(f"unresolved_new_events={unresolved['unresolved_new']}")

    print()
    print("TRADE_CONTEXT_NO_MISSING_GUARD_VALIDATION_SUMMARY")
    print(f"failures={len(failures)}")

    if failures:
        print("FAILURES=" + ",".join(failures))
        print("VERDICT=TRADE_CONTEXT_NO_MISSING_GUARD_VALIDATION_FAILED")
        return 1

    print("FAILURES=none")
    print("VERDICT=TRADE_CONTEXT_NO_MISSING_GUARD_VALIDATION_OK")
    print("TRADE_CONTEXT_NO_MISSING_GUARD_VALIDATION_V1_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
