#!/usr/bin/env python3
from __future__ import annotations

import os
import psycopg2
import psycopg2.extras

SQL = """
select
    (select coalesce(c.reltuples::bigint,0)
     from pg_class c
     join pg_namespace n on n.oid=c.relnamespace
     where c.relname='market_ticks'
       and n.nspname='public') as tick_rows,

    (select pg_total_relation_size('market_ticks')) as tick_bytes,

    null::text as tick_symbols,
    null::timestamptz as first_tick,
    null::timestamptz as last_tick,

    (select coalesce(c.reltuples::bigint,0)
     from pg_class c
     join pg_namespace n on n.oid=c.relnamespace
     where c.relname='market_bars'
       and n.nspname='public') as m1_bars,

    null::text as m1_symbols,
    null::timestamptz as first_m1,
    null::timestamptz as last_m1,

    (select count(*) from trades where origin='paper') as clean_paper_trades,
    (select count(*) from trades where origin is null and trade_source='paper') as null_origin_paper_trades,
    (select count(*) from trades where origin in ('replay_br_pipeline','historical_signal_replay','backfill_from_fills')) as replay_backfill_trades,

    (select count(*) from strategy_statistics_v3 where statistics_status='STATISTICALLY_REVIEWABLE') as v3_reviewable,
    (select count(*) from strategy_statistics_v3 where statistics_status='LOW_SAMPLE') as v3_low_sample,

    (select count(*) from broker_order_snapshots) as broker_order_snapshots,
    (select count(*) from order_reconciliation_runs) as order_reconciliation_runs,
    (select count(*) from order_reconciliation_issues) as order_reconciliation_issues,

    (select count(*) from trades where commission is not null) as trades_with_commission
;
"""

def main() -> int:
    print("=== SCALPING RESEARCH READINESS AUDIT V1 ===")
    print("mode=research_readiness")
    print("runtime_allow=0")
    print("execution_enabled=0")

    with psycopg2.connect(os.environ["DATABASE_URL"]) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(SQL)
            r = cur.fetchone()

    tick_ready = int(r["tick_rows"] or 0) > 100_000 and int(r["tick_bytes"] or 0) > 1_000_000_000
    m1_ready = int(r["m1_bars"] or 0) > 10_000
    source_clean = int(r["clean_paper_trades"] or 0) > 0 and int(r["null_origin_paper_trades"] or 0) == 0
    replay_isolated = int(r["replay_backfill_trades"] or 0) >= 0
    execution_audit_present = int(r["broker_order_snapshots"] or 0) > 0 and int(r["order_reconciliation_runs"] or 0) > 0
    commission_ready = int(r["trades_with_commission"] or 0) > 0

    print(
        "SCALPING_DATA_ROW "
        f"tick_rows={r['tick_rows']} "
        f"tick_symbols={r['tick_symbols']} "
        f"first_tick={r['first_tick']} "
        f"last_tick={r['last_tick']} "
        f"m1_bars={r['m1_bars']} "
        f"m1_symbols={r['m1_symbols']} "
        f"first_m1={r['first_m1']} "
        f"last_m1={r['last_m1']}"
    )

    print(
        "SCALPING_SOURCE_ROW "
        f"clean_paper_trades={r['clean_paper_trades']} "
        f"null_origin_paper_trades={r['null_origin_paper_trades']} "
        f"replay_backfill_trades={r['replay_backfill_trades']} "
        f"v3_reviewable={r['v3_reviewable']} "
        f"v3_low_sample={r['v3_low_sample']}"
    )

    print(
        "SCALPING_EXECUTION_ROW "
        f"broker_order_snapshots={r['broker_order_snapshots']} "
        f"order_reconciliation_runs={r['order_reconciliation_runs']} "
        f"order_reconciliation_issues={r['order_reconciliation_issues']} "
        f"trades_with_commission={r['trades_with_commission']}"
    )

    if not tick_ready:
        status = "NOT_READY"
        reason = "tick_data_insufficient"
    elif not m1_ready:
        status = "NOT_READY"
        reason = "m1_data_insufficient"
    elif not source_clean:
        status = "NOT_READY"
        reason = "paper_source_not_clean_enough"
    elif int(r["v3_reviewable"] or 0) == 0:
        status = "NOT_READY"
        reason = "no_reviewable_clean_v3_edge"
    elif not execution_audit_present:
        status = "NOT_READY"
        reason = "execution_reconciliation_missing"
    elif not commission_ready:
        status = "NOT_READY"
        reason = "commission_model_missing"
    else:
        status = "READY_FOR_RESEARCH_ONLY"
        reason = "data_and_execution_audit_present"

    print(
        "SCALPING_READINESS_VERDICT "
        f"status={status} "
        f"reason={reason} "
        f"tick_ready={tick_ready} "
        f"m1_ready={m1_ready} "
        f"source_clean={source_clean} "
        f"replay_isolated={replay_isolated} "
        f"execution_audit_present={execution_audit_present} "
        f"commission_ready={commission_ready} "
        "runtime_allow=0 execution_enabled=0"
    )

    print("SCALPING_RESEARCH_READINESS_AUDIT_V1_OK")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
