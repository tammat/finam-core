#!/usr/bin/env python3

import os
import psycopg2
import psycopg2.extras

DATABASE_URL = os.environ["DATABASE_URL"]

SQL = """
with base as (
    select
        id,
        net_pnl,
        coalesce(payload->'entry_payload'->>'reason','UNKNOWN') as entry_reason,
        coalesce(payload->'entry_payload'->'features'->>'regime','UNKNOWN') as regime
    from closed_trades
    where root_symbol='NG'
      and source='closed_trade_engine_v1_1'
),
marked as (
    select
        *,
        case
            when entry_reason='smart_entry_retest'
             and regime='trend_down_high_vol'
            then true else false
        end as blocked_by_gate
    from base
)
select
    case when blocked_by_gate then 'BLOCKED' else 'KEPT' end as bucket,
    count(*) trades,
    round(sum(net_pnl)::numeric,6) net_pnl,
    round(avg(net_pnl)::numeric,6) expectancy,
    round(
        100.0 * sum(case when net_pnl > 0 then 1 else 0 end) / nullif(count(*),0),
        2
    ) winrate
from marked
group by 1
order by bucket;
"""

def main():
    print("=== NG QUALITY GATE EFFECTIVENESS V1 ===")
    print("mode=research_only")
    print("execution=disabled")
    print("runtime_changed=0")
    print("rule=smart_entry_retest_and_trend_down_high_vol_block")
    print()

    with psycopg2.connect(DATABASE_URL) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(SQL)
            rows = cur.fetchall()

    print("GATE_EFFECTIVENESS")
    total_pnl = 0.0
    kept_pnl = 0.0
    blocked_pnl = 0.0

    for r in rows:
        pnl = float(r["net_pnl"])
        total_pnl += pnl
        if r["bucket"] == "KEPT":
            kept_pnl = pnl
        if r["bucket"] == "BLOCKED":
            blocked_pnl = pnl

        print(
            "GATE_ROW "
            f"bucket={r['bucket']} "
            f"trades={r['trades']} "
            f"net_pnl={r['net_pnl']} "
            f"expectancy={r['expectancy']} "
            f"winrate={r['winrate']}"
        )

    print()
    print(f"CURRENT_NET_PNL={round(total_pnl,6)}")
    print(f"GOVERNED_NET_PNL={round(kept_pnl,6)}")
    print(f"DELTA_PNL={round(kept_pnl - total_pnl,6)}")
    print(f"BLOCKED_NET_PNL={round(blocked_pnl,6)}")

    verdict = "NG_QUALITY_GATE_SUPPORTED" if kept_pnl > total_pnl else "NG_QUALITY_GATE_NOT_SUPPORTED"
    print(f"VERDICT={verdict}")
    print("NG_QUALITY_GATE_EFFECTIVENESS_V1_OK")

if __name__ == "__main__":
    main()
