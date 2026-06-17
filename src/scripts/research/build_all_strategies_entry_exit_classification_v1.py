#!/usr/bin/env python3
from __future__ import annotations

import os
import psycopg2
import psycopg2.extras


SQL = """
with fills as (
    select
        symbol,
        coalesce(strategy,'') as strategy,
        coalesce(timeframe,'') as timeframe,
        coalesce(trade_source,'') as trade_source,
        count(*) as fills,
        count(*) filter (where side='BUY') as buy_fills,
        count(*) filter (where side='SELL') as sell_fills,
        coalesce(sum(case when side='BUY' then qty when side='SELL' then -qty else 0 end),0) as net_qty,
        count(distinct created_at::date) as trade_days,
        min(created_at) as first_fill_ts,
        max(created_at) as last_fill_ts,
        max(created_at) filter (where side='BUY') as last_buy_ts,
        max(created_at) filter (where side='SELL') as last_sell_ts,
        count(*) filter (
            where coalesce(strategy,'') = ''
               or coalesce(timeframe,'') = ''
               or coalesce(strategy,'') in ('UNKNOWN', 'UNKNOWN_STRATEGY')
               or coalesce(timeframe,'') in ('UNKNOWN', 'UNKNOWN_TIMEFRAME', 'LIVE')
        ) as bad_identity_fills
    from trades
    where coalesce(trade_source,'')='paper'
      and coalesce(is_invalid,false)=false
    group by 1,2,3,4
),
chains as (
    select
        symbol,
        strategy,
        timeframe,
        trade_source,
        count(*) as chains,
        count(*) filter (where quality_status='FULL') as full_chains,
        count(*) filter (where quality_status='PARTIAL') as partial_chains,
        round(coalesce(sum(net_pnl),0),6) as pnl
    from closed_trade_chains_v3
    group by 1,2,3,4
),
joined as (
    select
        f.*,
        coalesce(c.chains,0) as chains,
        coalesce(c.full_chains,0) as full_chains,
        coalesce(c.partial_chains,0) as partial_chains,
        coalesce(c.pnl,0) as pnl
    from fills f
    left join chains c
      on c.symbol=f.symbol
     and c.strategy=f.strategy
     and c.timeframe=f.timeframe
     and c.trade_source=f.trade_source
)
select
    *,
    case
        when bad_identity_fills > 0
             and full_chains = 0
             then 'LEGACY_BAD_IDENTITY'

        when strategy in (
            'NG_CONSERVATIVE_BREAKOUT',
            'NG_CONSERVATIVE_BREAKOUT_M1',
            'BR_CONSERVATIVE_BREAKOUT',
            'USD_INTRADAY_REGIME',
            'gold_short_only_shadow_v1'
        )
        and full_chains > 0
        and abs(net_qty) > 0
             then 'OPEN_FORWARD_POSITION'

        when strategy in (
            'NG_CONSERVATIVE_BREAKOUT',
            'NG_CONSERVATIVE_BREAKOUT_M1',
            'BR_CONSERVATIVE_BREAKOUT',
            'USD_INTRADAY_REGIME',
            'gold_short_only_shadow_v1'
        )
        and full_chains > 0
             then 'CLEAN_V3_ACTIVE'

        when strategy in ('HISTORICAL_BREAKOUT_V1')
             then 'HISTORICAL_BATCH_NO_CHAINS'

        when strategy in (
            'NG_CONSERVATIVE_BREAKOUT',
            'NG_CONSERVATIVE_BREAKOUT_M1'
        )
        and fills >= 50
        and full_chains = 0
        and trade_days <= 1
             then 'REPLAY_OR_BURST_ARTIFACT'

        when fills >= 2 and full_chains = 0
             then 'NO_CHAINS_REVIEW'

        else 'NEEDS_MANUAL_REVIEW'
    end as classification
from joined
order by
    case
        when bad_identity_fills > 0 then 0
        when abs(net_qty) > 0 then 1
        when full_chains = 0 then 2
        else 3
    end,
    symbol,
    strategy,
    timeframe;
"""


CLASSIFIED_SQL = SQL.strip().rstrip(";")

SUMMARY_SQL = f"""
with classified as (
{CLASSIFIED_SQL}
)
select
    classification,
    count(*) as rows,
    sum(fills) as fills,
    sum(buy_fills) as buy_fills,
    sum(sell_fills) as sell_fills,
    round(sum(pnl),6) as pnl
from classified
group by classification
order by rows desc;
"""


def main() -> int:
    print("=== ALL STRATEGIES ENTRY EXIT CLASSIFICATION V1 ===")
    print("mode=diagnostic")
    print("runtime_allow=0")
    print("execution_enabled=0")

    with psycopg2.connect(os.environ["DATABASE_URL"]) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(SUMMARY_SQL)
            summary = cur.fetchall()

            cur.execute(SQL)
            rows = cur.fetchall()

    print()
    print("CLASSIFICATION_SUMMARY")
    for r in summary:
        print(
            "CLASSIFICATION_SUMMARY_ROW "
            f"classification={r['classification']} "
            f"rows={r['rows']} "
            f"fills={r['fills']} "
            f"buy={r['buy_fills']} "
            f"sell={r['sell_fills']} "
            f"pnl={r['pnl']}"
        )

    print()
    print("CLASSIFICATION_ROWS")
    for r in rows:
        print(
            "CLASSIFICATION_ROW "
            f"symbol={r['symbol']} "
            f"strategy={r['strategy'] or '<EMPTY>'} "
            f"timeframe={r['timeframe'] or '<EMPTY>'} "
            f"fills={r['fills']} "
            f"buy={r['buy_fills']} "
            f"sell={r['sell_fills']} "
            f"net_qty={float(r['net_qty'] or 0):.6f} "
            f"days={r['trade_days']} "
            f"full_chains={r['full_chains']} "
            f"partial_chains={r['partial_chains']} "
            f"pnl={float(r['pnl'] or 0):.6f} "
            f"bad_identity={r['bad_identity_fills']} "
            f"classification={r['classification']}"
        )

    legacy_bad = sum(1 for r in rows if r["classification"] == "LEGACY_BAD_IDENTITY")
    open_pos = sum(1 for r in rows if r["classification"] == "OPEN_FORWARD_POSITION")
    clean = sum(1 for r in rows if r["classification"] == "CLEAN_V3_ACTIVE")

    print()
    print(
        "CLASSIFICATION_TOTALS "
        f"legacy_bad_identity={legacy_bad} "
        f"open_forward_positions={open_pos} "
        f"clean_v3_active={clean}"
    )

    print("VERDICT=CLASSIFICATION_READY")
    print("ALL_STRATEGIES_ENTRY_EXIT_CLASSIFICATION_V1_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
