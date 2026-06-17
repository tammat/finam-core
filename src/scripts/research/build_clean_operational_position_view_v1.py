#!/usr/bin/env python3
from __future__ import annotations

import os
import psycopg2
import psycopg2.extras


CREATE_VIEW_SQL = """
-- Русский комментарий:
-- Сначала удаляем зависимое metrics-view, иначе PostgreSQL не даст
-- пересоздать базовое clean_operational_position_view_v1.
drop view if exists clean_operational_position_metrics_v1;

drop view if exists clean_operational_position_view_v1;

create view clean_operational_position_view_v1 as
with fills as (
    select
        symbol,
        strategy,
        timeframe,
        coalesce(trade_source, '') as trade_source,
        count(*) as fills,
        count(*) filter (where side='BUY') as buy_fills,
        count(*) filter (where side='SELL') as sell_fills,
        coalesce(sum(
            case
                when side='BUY' then qty
                when side='SELL' then -qty
                else 0
            end
        ),0) as net_qty,
        max(created_at) as last_fill_ts,
        max(created_at) filter (where side='BUY') as last_buy_ts,
        max(created_at) filter (where side='SELL') as last_sell_ts
    from trades
    where coalesce(trade_source,'')='paper'
      and coalesce(is_invalid,false)=false
      and coalesce(strategy,'') <> ''
      and coalesce(timeframe,'') <> ''
    group by symbol, strategy, timeframe, coalesce(trade_source, '')
),
chains as (
    select
        symbol,
        strategy,
        timeframe,
        trade_source,
        count(*) as full_chains,
        round(coalesce(sum(net_pnl),0),6) as v3_pnl,
        max(exit_ts) as last_chain_exit_ts
    from closed_trade_chains_v3
    where quality_status='FULL'
      and trade_source='paper'
    group by symbol, strategy, timeframe, trade_source
),
base as (
    select
        f.symbol,
        f.strategy,
        f.timeframe,
        f.trade_source,
        f.fills,
        f.buy_fills,
        f.sell_fills,
        f.net_qty,
        f.last_fill_ts,
        f.last_buy_ts,
        f.last_sell_ts,
        coalesce(c.full_chains,0) as full_chains,
        coalesce(c.v3_pnl,0) as v3_pnl,
        c.last_chain_exit_ts
    from fills f
    left join chains c
      on c.symbol=f.symbol
     and c.strategy=f.strategy
     and c.timeframe=f.timeframe
     and c.trade_source=f.trade_source
),
classified as (
    select
        *,
        case
            -- Русский комментарий:
            -- BRM6 хвост признан историческим partial tail.
            -- Он не отражает текущую operational paper-позицию.
            when symbol='BRM6@RTSX'
             and strategy='BR_CONSERVATIVE_BREAKOUT'
             and timeframe='M5'
                then 'EXCLUDE_HISTORICAL_TAIL'

            -- Русский комментарий:
            -- USDRUBF содержит загрязнённый хвост: разрыв цен 73.x -> 100.x
            -- и ранее был ограничен duration/contamination guard.
            when symbol='USDRUBF@RTSX'
             and strategy='USD_INTRADAY_REGIME'
             and timeframe='M5'
                then 'QUARANTINE_CONTAMINATED_TAIL'

            -- Русский комментарий:
            -- BRN6 — единственный оставляемый текущий paper-long tail.
            when symbol='BRN6@RTSX'
             and strategy='BR_CONSERVATIVE_BREAKOUT'
             and timeframe='M5'
             and abs(net_qty) > 0
                then 'OPEN_PAPER_LONG_TAIL'

            when full_chains > 0
             and abs(net_qty) = 0
                then 'CLEAN_V3_FLAT'

            when full_chains > 0
             and abs(net_qty) > 0
                then 'CLEAN_V3_OPEN_REVIEW'

            else 'OUT_OF_SCOPE'
        end as operational_status
    from base
)
select
    symbol,
    strategy,
    timeframe,
    trade_source,
    fills,
    buy_fills,
    sell_fills,
    net_qty,
    full_chains,
    v3_pnl,
    last_fill_ts,
    last_buy_ts,
    last_sell_ts,
    last_chain_exit_ts,
    operational_status,
    case
        when operational_status='OPEN_PAPER_LONG_TAIL' then true
        else false
    end as is_current_operational_position,
    case
        when operational_status in ('CLEAN_V3_FLAT', 'OPEN_PAPER_LONG_TAIL', 'CLEAN_V3_OPEN_REVIEW') then true
        else false
    end as include_in_clean_operational_view
from classified
where operational_status <> 'OUT_OF_SCOPE';
"""


REPORT_SQL = """
select
    operational_status,
    count(*) as rows,
    round(sum(net_qty)::numeric,6) as net_qty_sum,
    sum(full_chains) as full_chains,
    round(sum(v3_pnl)::numeric,6) as pnl
from clean_operational_position_view_v1
group by operational_status
order by operational_status;
"""


ROWS_SQL = """
select
    symbol,
    strategy,
    timeframe,
    trade_source,
    fills,
    buy_fills,
    sell_fills,
    round(net_qty::numeric,6) as net_qty,
    full_chains,
    round(v3_pnl::numeric,6) as pnl,
    operational_status,
    is_current_operational_position,
    include_in_clean_operational_view,
    last_buy_ts,
    last_sell_ts,
    last_chain_exit_ts
from clean_operational_position_view_v1
order by
    case operational_status
        when 'OPEN_PAPER_LONG_TAIL' then 0
        when 'CLEAN_V3_OPEN_REVIEW' then 1
        when 'CLEAN_V3_FLAT' then 2
        when 'QUARANTINE_CONTAMINATED_TAIL' then 3
        when 'EXCLUDE_HISTORICAL_TAIL' then 4
        else 5
    end,
    symbol,
    strategy,
    timeframe;
"""


ASSERT_SQL = """
select
    count(*) filter (
        where symbol='BRN6@RTSX'
          and strategy='BR_CONSERVATIVE_BREAKOUT'
          and timeframe='M5'
          and operational_status='OPEN_PAPER_LONG_TAIL'
          and is_current_operational_position=true
          and include_in_clean_operational_view=true
    ) as brn6_open_ok,

    count(*) filter (
        where symbol='BRM6@RTSX'
          and strategy='BR_CONSERVATIVE_BREAKOUT'
          and timeframe='M5'
          and operational_status='EXCLUDE_HISTORICAL_TAIL'
          and is_current_operational_position=false
          and include_in_clean_operational_view=false
    ) as brm6_excluded_ok,

    count(*) filter (
        where symbol='USDRUBF@RTSX'
          and strategy='USD_INTRADAY_REGIME'
          and timeframe='M5'
          and operational_status='QUARANTINE_CONTAMINATED_TAIL'
          and is_current_operational_position=false
          and include_in_clean_operational_view=false
    ) as usdrubf_quarantine_ok,

    count(*) filter (
        where symbol='NGQ6@RTSX'
          and strategy='NG_CONSERVATIVE_BREAKOUT_M1'
          and timeframe='M1'
          and operational_status in ('CLEAN_V3_FLAT', 'CLEAN_V3_OPEN_REVIEW')
          and is_current_operational_position=false
          and include_in_clean_operational_view=true
    ) as ngq6_clean_ok
from clean_operational_position_view_v1;
"""


def main() -> int:
    print("=== CLEAN OPERATIONAL POSITION VIEW V1 ===")
    print("mode=create_view")
    print("runtime_allow=0")
    print("execution_enabled=0")

    with psycopg2.connect(os.environ["DATABASE_URL"]) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(CREATE_VIEW_SQL)
            conn.commit()

            cur.execute(REPORT_SQL)
            report = cur.fetchall()

            cur.execute(ROWS_SQL)
            rows = cur.fetchall()

            cur.execute(ASSERT_SQL)
            checks = cur.fetchone()

    print()
    print("OPERATIONAL_VIEW_SUMMARY")
    for r in report:
        print(
            "OPERATIONAL_SUMMARY_ROW "
            f"status={r['operational_status']} "
            f"rows={r['rows']} "
            f"net_qty_sum={r['net_qty_sum']} "
            f"full_chains={r['full_chains']} "
            f"pnl={r['pnl']}"
        )

    print()
    print("OPERATIONAL_VIEW_ROWS")
    for r in rows:
        print(
            "OPERATIONAL_ROW "
            f"symbol={r['symbol']} "
            f"strategy={r['strategy']} "
            f"timeframe={r['timeframe']} "
            f"fills={r['fills']} "
            f"buy={r['buy_fills']} "
            f"sell={r['sell_fills']} "
            f"net_qty={r['net_qty']} "
            f"full_chains={r['full_chains']} "
            f"pnl={r['pnl']} "
            f"status={r['operational_status']} "
            f"current_position={int(r['is_current_operational_position'])} "
            f"include_clean={int(r['include_in_clean_operational_view'])} "
            f"last_buy={r['last_buy_ts']} "
            f"last_sell={r['last_sell_ts']} "
            f"last_chain_exit={r['last_chain_exit_ts']}"
        )

    print()
    print(
        "OPERATIONAL_VIEW_CHECKS "
        f"brn6_open_ok={checks['brn6_open_ok']} "
        f"brm6_excluded_ok={checks['brm6_excluded_ok']} "
        f"usdrubf_quarantine_ok={checks['usdrubf_quarantine_ok']} "
        f"ngq6_clean_ok={checks['ngq6_clean_ok']}"
    )

    if (
        int(checks["brn6_open_ok"] or 0) == 1
        and int(checks["brm6_excluded_ok"] or 0) == 1
        and int(checks["usdrubf_quarantine_ok"] or 0) == 1
        and int(checks["ngq6_clean_ok"] or 0) == 1
    ):
        verdict = "CLEAN_OPERATIONAL_POSITION_VIEW_READY"
    else:
        verdict = "CLEAN_OPERATIONAL_POSITION_VIEW_CHECK_FAILED"

    print(f"VERDICT={verdict}")
    print("CLEAN_OPERATIONAL_POSITION_VIEW_V1_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
