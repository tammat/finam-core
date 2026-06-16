#!/usr/bin/env python3
from __future__ import annotations

import os
import psycopg2
import psycopg2.extras

SQL = """
with candidates as (
    select
        symbol,
        strategy,
        timeframe,
        trade_source
    from rebuild_candidates_v1
    where rebuild_status='PLANNED'
),
chain_stats as (
    select
        c.symbol,
        c.strategy,
        c.timeframe,
        c.trade_source,
        count(distinct a.closed_trade_id)::int as chains,
        count(*)::int as attribution_rows,
        count(distinct ch.entry_ts::date)::int as entry_days,
        count(distinct ch.exit_ts::date)::int as exit_days,
        min(ch.entry_ts) as first_entry,
        max(ch.exit_ts) as last_exit,
        count(*) filter (where a.attribution_quality='FULL')::int as full_ctx,
        count(*) filter (where a.attribution_quality='PARTIAL')::int as partial_ctx,
        count(*) filter (where a.attribution_quality='RISK_CONTEXT_WEAK')::int as weak_ctx,
        coalesce(sum(a.pnl),0) as pnl
    from candidates c
    left join trade_attribution_v2 a
      on a.symbol=c.symbol
     and a.strategy=c.strategy
     and a.timeframe=c.timeframe
     and a.trade_source=c.trade_source
    left join closed_trade_chains_v2 ch
      on ch.id=a.closed_trade_id
    group by c.symbol,c.strategy,c.timeframe,c.trade_source
),
fill_origin as (
    select
        c.symbol,
        c.strategy,
        c.timeframe,
        c.trade_source,
        coalesce(t.origin,'') as origin,
        coalesce(t.trade_source,'') as fill_trade_source,
        count(*)::int as fills,
        count(distinct t.id)::int as distinct_fills,
        min(t.created_at) as first_fill,
        max(t.created_at) as last_fill
    from candidates c
    left join trades t
      on t.symbol=c.symbol
     and coalesce(t.strategy,'') = c.strategy
     and coalesce(t.timeframe,'') = c.timeframe
     and coalesce(t.trade_source,'') = c.trade_source
    group by
        c.symbol,c.strategy,c.timeframe,c.trade_source,
        coalesce(t.origin,''),coalesce(t.trade_source,'')
)
select
    cs.symbol,
    cs.strategy,
    cs.timeframe,
    cs.trade_source,
    cs.chains,
    cs.attribution_rows,
    cs.entry_days,
    cs.exit_days,
    cs.first_entry,
    cs.last_exit,
    cs.full_ctx,
    cs.partial_ctx,
    cs.weak_ctx,
    cs.pnl,
    fo.origin,
    fo.fill_trade_source,
    fo.fills,
    fo.distinct_fills,
    fo.first_fill,
    fo.last_fill
from chain_stats cs
left join fill_origin fo
  on fo.symbol=cs.symbol
 and fo.strategy=cs.strategy
 and fo.timeframe=cs.timeframe
 and fo.trade_source=cs.trade_source
order by cs.symbol,cs.strategy,cs.timeframe,fo.fills desc;
"""

def verdict(row: dict) -> tuple[str, str]:
    chains = int(row["chains"] or 0)
    attr = int(row["attribution_rows"] or 0)
    entry_days = int(row["entry_days"] or 0)
    exit_days = int(row["exit_days"] or 0)
    full_ctx = int(row["full_ctx"] or 0)
    partial_ctx = int(row["partial_ctx"] or 0)
    origin = row["origin"] or ""

    if chains == 0 and attr == 0:
        return "NO_CHAIN_DATA", "нет_chains_и_attribution_для_кандидата"

    if chains == attr and chains >= 100 and full_ctx == 0 and partial_ctx > 0:
        return "CHAIN_RECONSTRUCTION_SUSPECT", "chains_созданы_массово_с_partial_context"

    if chains >= 100 and (entry_days < 10 or exit_days < 10):
        return "TIME_CONCENTRATION_SUSPECT", "много_chains_при_низкой_временной_диверсификации"

    if origin == "backfill_from_fills":
        return "BACKFILL_ORIGIN_SUSPECT", "fills_имеют_origin_backfill_from_fills"

    return "REVIEW_REQUIRED", "нужен_ручной_разбор_происхождения"

def main() -> int:
    print("=== CHAIN PROVENANCE AUDIT V1 ===")
    print("mode=research_only")
    print("runtime_allow=0")
    print("execution_enabled=0")

    with psycopg2.connect(os.environ["DATABASE_URL"]) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(SQL)
            rows = cur.fetchall()

    suspect = 0

    for r in rows:
        status, reason = verdict(r)
        if status != "REVIEW_REQUIRED":
            suspect += 1

        print(
            "CHAIN_PROVENANCE_ROW "
            f"symbol={r['symbol']} "
            f"strategy={r['strategy']} "
            f"timeframe={r['timeframe']} "
            f"source={r['trade_source']} "
            f"chains={int(r['chains'] or 0)} "
            f"attribution_rows={int(r['attribution_rows'] or 0)} "
            f"entry_days={int(r['entry_days'] or 0)} "
            f"exit_days={int(r['exit_days'] or 0)} "
            f"full_ctx={int(r['full_ctx'] or 0)} "
            f"partial_ctx={int(r['partial_ctx'] or 0)} "
            f"weak_ctx={int(r['weak_ctx'] or 0)} "
            f"pnl={float(r['pnl'] or 0):.6f} "
            f"origin={r['origin']} "
            f"fill_source={r['fill_trade_source']} "
            f"fills={int(r['fills'] or 0)} "
            f"distinct_fills={int(r['distinct_fills'] or 0)} "
            f"first_entry={r['first_entry']} "
            f"last_exit={r['last_exit']} "
            f"first_fill={r['first_fill']} "
            f"last_fill={r['last_fill']} "
            f"provenance_status={status} "
            f"reason={reason} "
            "runtime_allow=0 execution_enabled=0"
        )

    print(
        "CHAIN_PROVENANCE_AUDIT_SUMMARY "
        f"rows={len(rows)} "
        f"suspect_rows={suspect} "
        "runtime_allow=0 execution_enabled=0"
    )
    print("CHAIN_PROVENANCE_AUDIT_V1_OK")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
