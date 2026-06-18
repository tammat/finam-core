#!/usr/bin/env python3
from __future__ import annotations

import os
import psycopg2
from psycopg2.extras import RealDictCursor


SUMMARY_SQL = """
with last_day as (
    select max(created_at::date) as trade_date
    from trades
),
base as (
    select
        t.*
    from trades t
    join last_day d on t.created_at::date = d.trade_date
    where t.trade_source = 'paper'
      and t.is_invalid = false
),
agg as (
    select
        symbol,
        coalesce(nullif(strategy, ''), 'UNKNOWN') as strategy,
        coalesce(nullif(timeframe, ''), 'UNKNOWN') as timeframe,
        count(*) as trades,
        sum(case when upper(side) = 'BUY' then qty else 0 end) as buy_qty,
        sum(case when upper(side) = 'SELL' then qty else 0 end) as sell_qty,
        sum(case when upper(side) = 'BUY' then qty * price else 0 end) as buy_value,
        sum(case when upper(side) = 'SELL' then qty * price else 0 end) as sell_value,
        sum(coalesce(commission, 0)) as commission,
        min(created_at) as first_trade,
        max(created_at) as last_trade
    from base
    group by symbol, coalesce(nullif(strategy, ''), 'UNKNOWN'), coalesce(nullif(timeframe, ''), 'UNKNOWN')
)
select
    symbol,
    strategy,
    timeframe,
    trades,
    buy_qty,
    sell_qty,
    buy_qty - sell_qty as net_qty,
    sell_value - buy_value as gross_pnl,
    sell_value - buy_value - commission as net_pnl,
    commission,
    first_trade,
    last_trade,
    case
        when buy_qty - sell_qty <> 0 then 'OPEN_TAIL_EXCLUDED_FROM_EDGE'
        when sell_value - buy_value - commission > 0 then 'EDGE_CANDIDATE_DAY_POSITIVE'
        when sell_value - buy_value - commission > -0.05 then 'EDGE_FLAT_OR_WEAK'
        else 'EDGE_NEGATIVE_DAY'
    end as edge_status
from agg
order by
    case when buy_qty - sell_qty = 0 then 0 else 1 end,
    net_pnl desc,
    symbol;
"""


TOTAL_SQL = """
with last_day as (
    select max(created_at::date) as trade_date
    from trades
),
base as (
    select
        t.*
    from trades t
    join last_day d on t.created_at::date = d.trade_date
    where t.trade_source = 'paper'
      and t.is_invalid = false
),
agg as (
    select
        symbol,
        sum(case when upper(side) = 'BUY' then qty else 0 end) as buy_qty,
        sum(case when upper(side) = 'SELL' then qty else 0 end) as sell_qty,
        sum(case when upper(side) = 'BUY' then qty * price else 0 end) as buy_value,
        sum(case when upper(side) = 'SELL' then qty * price else 0 end) as sell_value,
        sum(coalesce(commission, 0)) as commission,
        count(*) as trades
    from base
    group by symbol
),
classified as (
    select
        *,
        buy_qty - sell_qty as net_qty,
        sell_value - buy_value - commission as net_pnl
    from agg
)
select
    count(*) as symbols,
    sum(trades) as trades,
    count(*) filter (where net_qty = 0) as closed_symbols,
    count(*) filter (where net_qty <> 0) as open_tail_symbols,
    sum(net_pnl) filter (where net_qty = 0) as closed_net_pnl,
    sum(net_pnl) as rough_total_net_pnl,
    count(*) filter (where net_qty = 0 and net_pnl > 0) as positive_closed_symbols,
    count(*) filter (where net_qty = 0 and net_pnl <= 0) as negative_closed_symbols
from classified;
"""


def main() -> int:
    dsn = os.getenv("DATABASE_URL", "dbname=finam_core user=postgres")

    print("=== CLOSED TRADE EDGE SCORECARD V1 ===")
    print("mode=diagnostic")
    print("runtime_allow=0")
    print("execution_enabled=0")

    with psycopg2.connect(dsn) as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(TOTAL_SQL)
            total = cur.fetchone()

            print()
            print("CLOSED_TRADE_EDGE_SUMMARY")
            for key, value in total.items():
                print(f"{key}={value}")

            cur.execute(SUMMARY_SQL)
            rows = cur.fetchall()

            print()
            print("CLOSED_TRADE_EDGE_ROWS")
            for row in rows:
                print(
                    "EDGE_ROW "
                    f"symbol={row['symbol']} "
                    f"strategy={row['strategy']} "
                    f"timeframe={row['timeframe']} "
                    f"trades={row['trades']} "
                    f"buy_qty={row['buy_qty']} "
                    f"sell_qty={row['sell_qty']} "
                    f"net_qty={row['net_qty']} "
                    f"gross_pnl={row['gross_pnl']:.6f} "
                    f"net_pnl={row['net_pnl']:.6f} "
                    f"commission={row['commission']:.6f} "
                    f"edge_status={row['edge_status']} "
                    f"first_trade={row['first_trade']} "
                    f"last_trade={row['last_trade']}"
                )

    print()
    print("VERDICT=CLOSED_TRADE_EDGE_SCORECARD_READY")
    print("CLOSED_TRADE_EDGE_SCORECARD_V1_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
