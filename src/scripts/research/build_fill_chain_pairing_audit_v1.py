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
chains as (
    select
        a.symbol,
        a.strategy,
        a.timeframe,
        a.trade_source,
        a.closed_trade_id,
        c.entry_ts,
        c.exit_ts,
        a.pnl,
        a.attribution_quality
    from candidates rc
    join trade_attribution_v2 a
      on a.symbol=rc.symbol
     and a.strategy=rc.strategy
     and a.timeframe=rc.timeframe
     and a.trade_source=rc.trade_source
    join closed_trade_chains_v2 c
      on c.id=a.closed_trade_id
),
paired as (
    select
        ch.symbol,
        ch.strategy,
        ch.timeframe,
        ch.trade_source,
        ch.closed_trade_id,
        ch.entry_ts,
        ch.exit_ts,
        ch.pnl,
        ch.attribution_quality,

        count(t.id)::int as fills_in_window,
        count(t.id) filter (
            where coalesce(t.strategy,'') = ch.strategy
              and coalesce(t.timeframe,'') = ch.timeframe
        )::int as fills_same_strategy_timeframe,

        count(t.id) filter (
            where coalesce(t.origin,'') = 'backfill_from_fills'
        )::int as backfill_fills,

        count(t.id) filter (
            where coalesce(t.origin,'') like '%replay%'
        )::int as replay_fills,

        count(t.id) filter (
            where coalesce(t.origin,'') = 'paper'
        )::int as paper_fills,

        min(t.created_at) as first_fill,
        max(t.created_at) as last_fill
    from chains ch
    left join trades t
      on t.symbol=ch.symbol
     and t.trade_source=ch.trade_source
     and t.created_at between ch.entry_ts and ch.exit_ts
    group by
        ch.symbol,
        ch.strategy,
        ch.timeframe,
        ch.trade_source,
        ch.closed_trade_id,
        ch.entry_ts,
        ch.exit_ts,
        ch.pnl,
        ch.attribution_quality
),
summary as (
    select
        symbol,
        strategy,
        timeframe,
        trade_source,

        count(*)::int as chains,
        count(*) filter (where fills_in_window > 0)::int as chains_with_any_fill,
        count(*) filter (where fills_same_strategy_timeframe > 0)::int as chains_with_exact_strategy_tf_fill,
        count(*) filter (where fills_in_window = 0)::int as chains_without_fill,

        count(*) filter (
            where fills_in_window > 0
              and fills_same_strategy_timeframe = 0
        )::int as chains_with_symbol_only_fill,

        count(*) filter (where backfill_fills > 0)::int as chains_with_backfill_fill,
        count(*) filter (where replay_fills > 0)::int as chains_with_replay_fill,
        count(*) filter (where paper_fills > 0)::int as chains_with_paper_fill,

        count(*) filter (where attribution_quality='FULL')::int as full_ctx,
        count(*) filter (where attribution_quality='PARTIAL')::int as partial_ctx,
        count(*) filter (where attribution_quality='RISK_CONTEXT_WEAK')::int as weak_ctx,

        count(distinct entry_ts::date)::int as entry_days,
        count(distinct exit_ts::date)::int as exit_days,

        min(entry_ts) as first_entry,
        max(exit_ts) as last_exit,

        coalesce(sum(pnl),0) as pnl
    from paired
    group by symbol,strategy,timeframe,trade_source
)
select *
from summary
order by symbol,strategy,timeframe;
"""

def status(row: dict) -> tuple[str, str]:
    chains = int(row["chains"] or 0)
    exact = int(row["chains_with_exact_strategy_tf_fill"] or 0)
    any_fill = int(row["chains_with_any_fill"] or 0)
    no_fill = int(row["chains_without_fill"] or 0)
    full_ctx = int(row["full_ctx"] or 0)
    partial_ctx = int(row["partial_ctx"] or 0)

    if chains == 0:
        return "NO_CHAINS", "нет_closed_trade_chains"

    if exact == 0 and no_fill == chains:
        return "UNSUPPORTED_BY_FILLS", "chains_не_подтверждены_fills"

    if exact == 0 and any_fill > 0:
        return "SYMBOL_ONLY_FILL_MATCH", "есть_fills_по_symbol_но_нет_точного_strategy_timeframe"

    if exact < chains:
        return "PARTIALLY_SUPPORTED_BY_FILLS", "часть_chains_не_имеет_точного_fill_подтверждения"

    if full_ctx == 0 and partial_ctx > 0:
        return "SUPPORTED_BUT_PARTIAL_CONTEXT", "fills_есть_но_context_неполный"

    return "SUPPORTED_BY_FILLS", "chains_подтверждены_fills"

def main() -> int:
    print("=== FILL CHAIN PAIRING AUDIT V1 ===")
    print("mode=research_only")
    print("runtime_allow=0")
    print("execution_enabled=0")

    with psycopg2.connect(os.environ["DATABASE_URL"]) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(SQL)
            rows = cur.fetchall()

    unsupported = 0
    partial = 0
    supported = 0

    for r in rows:
        st, reason = status(r)

        if st in {"UNSUPPORTED_BY_FILLS", "SYMBOL_ONLY_FILL_MATCH"}:
            unsupported += 1
        elif st in {"PARTIALLY_SUPPORTED_BY_FILLS", "SUPPORTED_BUT_PARTIAL_CONTEXT"}:
            partial += 1
        else:
            supported += 1

        print(
            "FILL_CHAIN_PAIRING_ROW "
            f"symbol={r['symbol']} "
            f"strategy={r['strategy']} "
            f"timeframe={r['timeframe']} "
            f"source={r['trade_source']} "
            f"chains={int(r['chains'] or 0)} "
            f"chains_with_any_fill={int(r['chains_with_any_fill'] or 0)} "
            f"chains_with_exact_strategy_tf_fill={int(r['chains_with_exact_strategy_tf_fill'] or 0)} "
            f"chains_without_fill={int(r['chains_without_fill'] or 0)} "
            f"chains_with_symbol_only_fill={int(r['chains_with_symbol_only_fill'] or 0)} "
            f"backfill_chains={int(r['chains_with_backfill_fill'] or 0)} "
            f"replay_chains={int(r['chains_with_replay_fill'] or 0)} "
            f"paper_chains={int(r['chains_with_paper_fill'] or 0)} "
            f"full_ctx={int(r['full_ctx'] or 0)} "
            f"partial_ctx={int(r['partial_ctx'] or 0)} "
            f"weak_ctx={int(r['weak_ctx'] or 0)} "
            f"entry_days={int(r['entry_days'] or 0)} "
            f"exit_days={int(r['exit_days'] or 0)} "
            f"pnl={float(r['pnl'] or 0):.6f} "
            f"first_entry={r['first_entry']} "
            f"last_exit={r['last_exit']} "
            f"pairing_status={st} "
            f"reason={reason} "
            "runtime_allow=0 execution_enabled=0"
        )

    print(
        "FILL_CHAIN_PAIRING_AUDIT_SUMMARY "
        f"rows={len(rows)} "
        f"unsupported={unsupported} "
        f"partial={partial} "
        f"supported={supported} "
        "runtime_allow=0 execution_enabled=0"
    )

    print("FILL_CHAIN_PAIRING_AUDIT_V1_OK")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
