#!/usr/bin/env python3
from __future__ import annotations

import os
import psycopg2
from psycopg2.extras import RealDictCursor


SQL = """
with base as (
    select
        id,
        symbol,
        side,
        qty,
        price,
        commission,
        origin,
        trade_source,
        strategy,
        timeframe,
        continuous_symbol,
        payload,
        created_at,
        is_invalid
    from trades
    where created_at::date = (
        select max(created_at::date)
        from trades
    )
),
classified as (
    select
        *,
        case when strategy is null or strategy = '' then 1 else 0 end as strategy_missing,
        case when timeframe is null or timeframe = '' then 1 else 0 end as timeframe_missing,
        case when continuous_symbol is null or continuous_symbol = '' then 1 else 0 end as continuous_symbol_missing,
        case when payload ? 'paper_only' then 1 else 0 end as payload_has_paper_only,
        case when payload ? 'execution_type' then 1 else 0 end as payload_has_execution_type,
        case when payload ? 'payload' then 1 else 0 end as payload_has_nested_payload
    from base
)
select
    symbol,
    origin,
    trade_source,
    count(*) as trades,
    sum(strategy_missing) as strategy_missing,
    sum(timeframe_missing) as timeframe_missing,
    sum(continuous_symbol_missing) as continuous_symbol_missing,
    sum(payload_has_paper_only) as payload_has_paper_only,
    sum(payload_has_execution_type) as payload_has_execution_type,
    sum(payload_has_nested_payload) as payload_has_nested_payload,
    min(created_at) as first_trade,
    max(created_at) as last_trade
from classified
group by symbol, origin, trade_source
order by trades desc, symbol, origin;
"""


SUMMARY_SQL = """
with base as (
    select
        *
    from trades
    where created_at::date = (
        select max(created_at::date)
        from trades
    )
)
select
    count(*) as trades_total,
    count(*) filter (where strategy is null or strategy = '') as strategy_missing,
    count(*) filter (where timeframe is null or timeframe = '') as timeframe_missing,
    count(*) filter (where continuous_symbol is null or continuous_symbol = '') as continuous_symbol_missing,
    count(*) filter (where payload ? 'paper_only') as payload_has_paper_only,
    count(*) filter (where payload ? 'execution_type') as payload_has_execution_type,
    count(*) filter (where payload ? 'payload') as payload_has_nested_payload,
    count(*) filter (where is_invalid = true) as invalid_trades,
    min(created_at::date) as trade_date
from base;
"""


def main() -> int:
    dsn = os.getenv("DATABASE_URL")
    if not dsn:
        dsn = "dbname=finam_core user=postgres"

    print("=== TRADE CONTEXT SNAPSHOT COMPLETENESS V1 ===")
    print("mode=diagnostic")
    print("runtime_allow=0")
    print("execution_enabled=0")

    with psycopg2.connect(dsn) as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(SUMMARY_SQL)
            summary = cur.fetchone()

            print()
            print("TRADE_CONTEXT_COMPLETENESS_SUMMARY")
            for key, value in summary.items():
                print(f"{key}={value}")

            cur.execute(SQL)
            rows = cur.fetchall()

            print()
            print("TRADE_CONTEXT_COMPLETENESS_ROWS")
            for row in rows:
                print(
                    "TRADE_CONTEXT_ROW "
                    f"symbol={row['symbol']} "
                    f"origin={row['origin']} "
                    f"trade_source={row['trade_source']} "
                    f"trades={row['trades']} "
                    f"strategy_missing={row['strategy_missing']} "
                    f"timeframe_missing={row['timeframe_missing']} "
                    f"continuous_symbol_missing={row['continuous_symbol_missing']} "
                    f"payload_has_paper_only={row['payload_has_paper_only']} "
                    f"payload_has_execution_type={row['payload_has_execution_type']} "
                    f"payload_has_nested_payload={row['payload_has_nested_payload']} "
                    f"first_trade={row['first_trade']} "
                    f"last_trade={row['last_trade']}"
                )

    print()
    print("VERDICT=TRADE_CONTEXT_SNAPSHOT_COMPLETENESS_REVIEW_READY")
    print("TRADE_CONTEXT_SNAPSHOT_COMPLETENESS_V1_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
