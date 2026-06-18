#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os

import psycopg2
from psycopg2.extras import RealDictCursor


PREVIEW_SQL = """
with last_day as (
    select max(created_at::date) as trade_date
    from trades
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
    from trades, last_day
    where created_at::date = last_day.trade_date
)
select
    count(*) as rows_total,
    count(*) filter (
        where (strategy is null or strategy = '')
          and payload_strategy is not null
    ) as strategy_updates,
    count(*) filter (
        where (timeframe is null or timeframe = '')
          and payload_timeframe is not null
    ) as timeframe_updates,
    count(*) filter (
        where (continuous_symbol is null or continuous_symbol = '')
          and payload_continuous_symbol is not null
    ) as continuous_symbol_updates
from candidate;
"""


DETAIL_SQL = """
with last_day as (
    select max(created_at::date) as trade_date
    from trades
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
    from trades, last_day
    where created_at::date = last_day.trade_date
)
select
    symbol,
    count(*) as trades,
    count(*) filter (
        where (strategy is null or strategy = '')
          and payload_strategy is not null
    ) as strategy_updates,
    count(*) filter (
        where (timeframe is null or timeframe = '')
          and payload_timeframe is not null
    ) as timeframe_updates,
    count(*) filter (
        where (continuous_symbol is null or continuous_symbol = '')
          and payload_continuous_symbol is not null
    ) as continuous_symbol_updates,
    min(created_at) as first_trade,
    max(created_at) as last_trade
from candidate
group by symbol
order by trades desc, symbol;
"""


APPLY_SQL = """
with last_day as (
    select max(created_at::date) as trade_date
    from trades
),
candidate as (
    select
        id,
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
        ) as payload_continuous_symbol
    from trades, last_day
    where created_at::date = last_day.trade_date
)
update trades t
set
    strategy = case
        when (t.strategy is null or t.strategy = '')
         and c.payload_strategy is not null
        then c.payload_strategy
        else t.strategy
    end,
    timeframe = case
        when (t.timeframe is null or t.timeframe = '')
         and c.payload_timeframe is not null
        then c.payload_timeframe
        else t.timeframe
    end,
    continuous_symbol = case
        when (t.continuous_symbol is null or t.continuous_symbol = '')
         and c.payload_continuous_symbol is not null
        then c.payload_continuous_symbol
        else t.continuous_symbol
    end
from candidate c
where t.id = c.id
  and (
        ((t.strategy is null or t.strategy = '') and c.payload_strategy is not null)
     or ((t.timeframe is null or t.timeframe = '') and c.payload_timeframe is not null)
     or ((t.continuous_symbol is null or t.continuous_symbol = '') and c.payload_continuous_symbol is not null)
  )
returning t.id, t.symbol, t.strategy, t.timeframe, t.continuous_symbol;
"""


VERIFY_SQL = """
with last_day as (
    select max(created_at::date) as trade_date
    from trades
)
select
    count(*) as trades_total,
    count(*) filter (where strategy is null or strategy = '') as strategy_missing,
    count(*) filter (where timeframe is null or timeframe = '') as timeframe_missing,
    count(*) filter (where continuous_symbol is null or continuous_symbol = '') as continuous_symbol_missing
from trades, last_day
where created_at::date = last_day.trade_date;
"""


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()

    dsn = os.getenv("DATABASE_URL", "dbname=finam_core user=postgres")

    print("=== APPLY TRADE CONTEXT BACKFILL FROM PAYLOAD V1 ===")
    print(f"mode={'apply' if args.apply else 'dry_run'}")
    print("runtime_allow=0")
    print("execution_enabled=0")

    with psycopg2.connect(dsn) as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(PREVIEW_SQL)
            preview = cur.fetchone()

            print()
            print("BACKFILL_APPLY_PREVIEW")
            for key, value in preview.items():
                print(f"{key}={value}")

            cur.execute(DETAIL_SQL)
            rows = cur.fetchall()

            print()
            print("BACKFILL_APPLY_DETAIL")
            for row in rows:
                print(
                    "BACKFILL_DETAIL_ROW "
                    f"symbol={row['symbol']} "
                    f"trades={row['trades']} "
                    f"strategy_updates={row['strategy_updates']} "
                    f"timeframe_updates={row['timeframe_updates']} "
                    f"continuous_symbol_updates={row['continuous_symbol_updates']} "
                    f"first_trade={row['first_trade']} "
                    f"last_trade={row['last_trade']}"
                )

            updated = 0
            if args.apply:
                cur.execute(APPLY_SQL)
                updated_rows = cur.fetchall()
                updated = len(updated_rows)
                conn.commit()
            else:
                conn.rollback()

            print()
            print(f"updated_rows={updated}")

            cur.execute(VERIFY_SQL)
            verify = cur.fetchone()

            print()
            print("BACKFILL_APPLY_VERIFY")
            for key, value in verify.items():
                print(f"{key}={value}")

    if args.apply:
        print("VERDICT=TRADE_CONTEXT_BACKFILL_FROM_PAYLOAD_APPLIED")
    else:
        print("VERDICT=TRADE_CONTEXT_BACKFILL_FROM_PAYLOAD_DRY_RUN_READY")

    print("APPLY_TRADE_CONTEXT_BACKFILL_FROM_PAYLOAD_V1_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
