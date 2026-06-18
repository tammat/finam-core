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
        coalesce(nullif(strategy, ''), 'UNKNOWN') as strategy,
        coalesce(nullif(timeframe, ''), 'UNKNOWN') as timeframe,
        coalesce(nullif(continuous_symbol, ''), symbol) as continuous_symbol,
        symbol,
        count(*) as trades,
        sum(case when upper(side) = 'BUY' then qty else 0 end) as buy_qty,
        sum(case when upper(side) = 'SELL' then qty else 0 end) as sell_qty,
        sum(case when upper(side) = 'BUY' then qty * price else 0 end) as buy_value,
        sum(case when upper(side) = 'SELL' then qty * price else 0 end) as sell_value,
        sum(coalesce(commission, 0)) as commission,
        min(created_at) as first_trade,
        max(created_at) as last_trade
    from base
    group by
        coalesce(nullif(strategy, ''), 'UNKNOWN'),
        coalesce(nullif(timeframe, ''), 'UNKNOWN'),
        coalesce(nullif(continuous_symbol, ''), symbol),
        symbol
),
scored as (
    select
        *,
        buy_qty - sell_qty as net_qty,
        sell_value - buy_value as gross_pnl,
        sell_value - buy_value - commission as net_pnl,
        case
            when count(*) over () = 0 then null
            else null
        end as unused
    from agg
)
select
    count(*) as rows_total,
    sum(trades) as trades_total,
    count(*) filter (where net_qty = 0) as closed_rows,
    count(*) filter (where net_qty <> 0) as open_tail_rows,
    sum(net_pnl) filter (where net_qty = 0) as closed_net_pnl,
    sum(gross_pnl) filter (where net_qty = 0) as closed_gross_pnl,
    sum(commission) filter (where net_qty = 0) as closed_commission,
    sum(net_pnl) as rough_total_net_pnl,
    count(*) filter (where net_qty = 0 and net_pnl > 0) as positive_closed_rows,
    count(*) filter (where net_qty = 0 and net_pnl <= 0) as negative_closed_rows,
    count(*) filter (where net_qty = 0 and gross_pnl > 0 and net_pnl <= 0) as commission_killed_rows
from scored;
"""


ROWS_SQL = """
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
        coalesce(nullif(strategy, ''), 'UNKNOWN') as strategy,
        coalesce(nullif(timeframe, ''), 'UNKNOWN') as timeframe,
        coalesce(nullif(continuous_symbol, ''), symbol) as continuous_symbol,
        symbol,
        count(*) as trades,
        sum(case when upper(side) = 'BUY' then qty else 0 end) as buy_qty,
        sum(case when upper(side) = 'SELL' then qty else 0 end) as sell_qty,
        sum(case when upper(side) = 'BUY' then qty * price else 0 end) as buy_value,
        sum(case when upper(side) = 'SELL' then qty * price else 0 end) as sell_value,
        sum(coalesce(commission, 0)) as commission,
        min(created_at) as first_trade,
        max(created_at) as last_trade
    from base
    group by
        coalesce(nullif(strategy, ''), 'UNKNOWN'),
        coalesce(nullif(timeframe, ''), 'UNKNOWN'),
        coalesce(nullif(continuous_symbol, ''), symbol),
        symbol
),
scored as (
    select
        *,
        buy_qty - sell_qty as net_qty,
        sell_value - buy_value as gross_pnl,
        sell_value - buy_value - commission as net_pnl,
        case
            when trades > 0 then (sell_value - buy_value - commission) / trades
            else null
        end as net_pnl_per_trade,
        case
            when abs(sell_value - buy_value) > 0 then commission / abs(sell_value - buy_value)
            else null
        end as commission_drag
    from agg
)
select
    strategy,
    timeframe,
    continuous_symbol,
    symbol,
    trades,
    buy_qty,
    sell_qty,
    net_qty,
    gross_pnl,
    commission,
    net_pnl,
    net_pnl_per_trade,
    commission_drag,
    first_trade,
    last_trade,
    case
        when net_qty <> 0 then 'OPEN_TAIL_REQUIRES_MTM'
        when net_pnl > 0 and trades >= 20 then 'EDGE_CANDIDATE_DAY_POSITIVE'
        when net_pnl > 0 then 'EDGE_POSITIVE_BUT_LOW_SAMPLE'
        when gross_pnl > 0 and net_pnl <= 0 then 'EDGE_KILLED_BY_COMMISSION'
        when net_pnl > -0.05 then 'EDGE_FLAT_OR_WEAK'
        else 'EDGE_NEGATIVE_DAY'
    end as edge_status
from scored
order by
    case when net_qty = 0 then 0 else 1 end,
    net_pnl desc,
    strategy,
    symbol;
"""


STRATEGY_SQL = """
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
        coalesce(nullif(strategy, ''), 'UNKNOWN') as strategy,
        coalesce(nullif(timeframe, ''), 'UNKNOWN') as timeframe,
        count(*) as trades,
        count(distinct symbol) as symbols,
        sum(case when upper(side) = 'BUY' then qty else 0 end) as buy_qty,
        sum(case when upper(side) = 'SELL' then qty else 0 end) as sell_qty,
        sum(case when upper(side) = 'BUY' then qty * price else 0 end) as buy_value,
        sum(case when upper(side) = 'SELL' then qty * price else 0 end) as sell_value,
        sum(coalesce(commission, 0)) as commission
    from base
    group by
        coalesce(nullif(strategy, ''), 'UNKNOWN'),
        coalesce(nullif(timeframe, ''), 'UNKNOWN')
),
scored as (
    select
        *,
        buy_qty - sell_qty as net_qty,
        sell_value - buy_value as gross_pnl,
        sell_value - buy_value - commission as net_pnl,
        case
            when trades > 0 then (sell_value - buy_value - commission) / trades
            else null
        end as net_pnl_per_trade,
        case
            when abs(sell_value - buy_value) > 0 then commission / abs(sell_value - buy_value)
            else null
        end as commission_drag
    from agg
)
select
    strategy,
    timeframe,
    symbols,
    trades,
    buy_qty,
    sell_qty,
    net_qty,
    gross_pnl,
    commission,
    net_pnl,
    net_pnl_per_trade,
    commission_drag,
    case
        when net_qty <> 0 then 'OPEN_TAIL_REQUIRES_MTM'
        when net_pnl > 0 and trades >= 20 then 'EDGE_CANDIDATE_DAY_POSITIVE'
        when net_pnl > 0 then 'EDGE_POSITIVE_BUT_LOW_SAMPLE'
        when gross_pnl > 0 and net_pnl <= 0 then 'EDGE_KILLED_BY_COMMISSION'
        when net_pnl > -0.05 then 'EDGE_FLAT_OR_WEAK'
        else 'EDGE_NEGATIVE_DAY'
    end as edge_status
from scored
order by
    case when net_qty = 0 then 0 else 1 end,
    net_pnl desc,
    strategy;
"""


def fmt(value: object, digits: int = 6) -> str:
    if value is None:
        return "None"
    if isinstance(value, float):
        return f"{value:.{digits}f}"
    return str(value)


def main() -> int:
    dsn = os.getenv("DATABASE_URL", "dbname=finam_core user=postgres")

    print("=== CLOSED TRADE EDGE SCORECARD V2 ===")
    print("mode=diagnostic")
    print("runtime_allow=0")
    print("execution_enabled=0")

    with psycopg2.connect(dsn) as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(SUMMARY_SQL)
            summary = cur.fetchone()

            print()
            print("CLOSED_TRADE_EDGE_V2_SUMMARY")
            for key, value in summary.items():
                print(f"{key}={fmt(value)}")

            cur.execute(STRATEGY_SQL)
            strategy_rows = cur.fetchall()

            print()
            print("CLOSED_TRADE_EDGE_V2_STRATEGY_ROWS")
            for row in strategy_rows:
                print(
                    "EDGE_V2_STRATEGY_ROW "
                    f"strategy={row['strategy']} "
                    f"timeframe={row['timeframe']} "
                    f"symbols={row['symbols']} "
                    f"trades={row['trades']} "
                    f"buy_qty={fmt(row['buy_qty'], 4)} "
                    f"sell_qty={fmt(row['sell_qty'], 4)} "
                    f"net_qty={fmt(row['net_qty'], 4)} "
                    f"gross_pnl={fmt(row['gross_pnl'])} "
                    f"commission={fmt(row['commission'])} "
                    f"net_pnl={fmt(row['net_pnl'])} "
                    f"net_pnl_per_trade={fmt(row['net_pnl_per_trade'])} "
                    f"commission_drag={fmt(row['commission_drag'])} "
                    f"edge_status={row['edge_status']}"
                )

            cur.execute(ROWS_SQL)
            rows = cur.fetchall()

            print()
            print("CLOSED_TRADE_EDGE_V2_SYMBOL_ROWS")
            for row in rows:
                print(
                    "EDGE_V2_SYMBOL_ROW "
                    f"strategy={row['strategy']} "
                    f"timeframe={row['timeframe']} "
                    f"continuous_symbol={row['continuous_symbol']} "
                    f"symbol={row['symbol']} "
                    f"trades={row['trades']} "
                    f"buy_qty={fmt(row['buy_qty'], 4)} "
                    f"sell_qty={fmt(row['sell_qty'], 4)} "
                    f"net_qty={fmt(row['net_qty'], 4)} "
                    f"gross_pnl={fmt(row['gross_pnl'])} "
                    f"commission={fmt(row['commission'])} "
                    f"net_pnl={fmt(row['net_pnl'])} "
                    f"net_pnl_per_trade={fmt(row['net_pnl_per_trade'])} "
                    f"commission_drag={fmt(row['commission_drag'])} "
                    f"edge_status={row['edge_status']} "
                    f"first_trade={row['first_trade']} "
                    f"last_trade={row['last_trade']}"
                )

    print()
    print("VERDICT=CLOSED_TRADE_EDGE_SCORECARD_V2_READY")
    print("CLOSED_TRADE_EDGE_SCORECARD_V2_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
