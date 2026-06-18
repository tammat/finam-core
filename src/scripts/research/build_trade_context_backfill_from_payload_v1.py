#!/usr/bin/env python3
from __future__ import annotations

import os
import psycopg2
from psycopg2.extras import RealDictCursor


PREVIEW_SQL = """
with last_day as (
    select max(created_at::date) as trade_date
    from trades
),
base as (
    select
        id,
        symbol,
        strategy,
        timeframe,
        continuous_symbol,
        payload,
        created_at
    from trades, last_day
    where created_at::date = last_day.trade_date
),
candidate as (
    select
        id,
        symbol,
        strategy,
        timeframe,
        continuous_symbol,
        coalesce(
            nullif(payload->>'strategy', ''),
            nullif(payload->'payload'->>'strategy', '')
        ) as payload_strategy,
        coalesce(
            nullif(payload->>'timeframe', ''),
            nullif(payload->'payload'->>'timeframe', '')
        ) as payload_timeframe,
        coalesce(
            nullif(payload->>'continuous_symbol', ''),
            nullif(payload->'payload'->>'continuous_symbol', '')
        ) as payload_continuous_symbol,
        created_at
    from base
)
select
    symbol,
    count(*) as trades,
    count(*) filter (where strategy is null or strategy = '') as strategy_missing,
    count(*) filter (where timeframe is null or timeframe = '') as timeframe_missing,
    count(*) filter (where continuous_symbol is null or continuous_symbol = '') as continuous_symbol_missing,
    count(*) filter (where payload_strategy is not null) as recoverable_strategy,
    count(*) filter (where payload_timeframe is not null) as recoverable_timeframe,
    count(*) filter (where payload_continuous_symbol is not null) as recoverable_continuous_symbol,
    count(*) filter (
        where (strategy is null or strategy = '')
          and payload_strategy is not null
    ) as strategy_backfill_candidates,
    count(*) filter (
        where (timeframe is null or timeframe = '')
          and payload_timeframe is not null
    ) as timeframe_backfill_candidates,
    count(*) filter (
        where (continuous_symbol is null or continuous_symbol = '')
          and payload_continuous_symbol is not null
    ) as continuous_symbol_backfill_candidates
from candidate
group by symbol
order by trades desc, symbol;
"""


def main() -> int:
    dsn = os.getenv("DATABASE_URL", "dbname=finam_core user=postgres")

    print("=== TRADE CONTEXT BACKFILL FROM PAYLOAD V1 ===")
    print("mode=preview")
    print("runtime_allow=0")
    print("execution_enabled=0")

    total_strategy_candidates = 0
    total_timeframe_candidates = 0
    total_cont_candidates = 0

    with psycopg2.connect(dsn) as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(PREVIEW_SQL)
            rows = cur.fetchall()

            print()
            print("TRADE_CONTEXT_BACKFILL_PREVIEW_ROWS")
            for row in rows:
                total_strategy_candidates += int(row["strategy_backfill_candidates"] or 0)
                total_timeframe_candidates += int(row["timeframe_backfill_candidates"] or 0)
                total_cont_candidates += int(row["continuous_symbol_backfill_candidates"] or 0)

                print(
                    "BACKFILL_PREVIEW_ROW "
                    f"symbol={row['symbol']} "
                    f"trades={row['trades']} "
                    f"strategy_missing={row['strategy_missing']} "
                    f"timeframe_missing={row['timeframe_missing']} "
                    f"continuous_symbol_missing={row['continuous_symbol_missing']} "
                    f"recoverable_strategy={row['recoverable_strategy']} "
                    f"recoverable_timeframe={row['recoverable_timeframe']} "
                    f"recoverable_continuous_symbol={row['recoverable_continuous_symbol']} "
                    f"strategy_backfill_candidates={row['strategy_backfill_candidates']} "
                    f"timeframe_backfill_candidates={row['timeframe_backfill_candidates']} "
                    f"continuous_symbol_backfill_candidates={row['continuous_symbol_backfill_candidates']}"
                )

    print()
    print("TRADE_CONTEXT_BACKFILL_PREVIEW_SUMMARY")
    print(f"strategy_backfill_candidates={total_strategy_candidates}")
    print(f"timeframe_backfill_candidates={total_timeframe_candidates}")
    print(f"continuous_symbol_backfill_candidates={total_cont_candidates}")

    if total_strategy_candidates == 0 and total_timeframe_candidates == 0:
        print("VERDICT=TRADE_CONTEXT_NOT_RECOVERABLE_FROM_PAYLOAD")
    else:
        print("VERDICT=TRADE_CONTEXT_BACKFILL_FROM_PAYLOAD_READY")

    print("TRADE_CONTEXT_BACKFILL_FROM_PAYLOAD_V1_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
