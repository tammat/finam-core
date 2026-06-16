#!/usr/bin/env python3
from __future__ import annotations

import os
import psycopg2
import psycopg2.extras

SQL = """
select
    symbol,
    strategy,
    timeframe,
    trade_source,
    trades,
    entry_days,
    exit_days,
    full_ctx_pct,
    identity_status,
    trusted_status,
    trusted_reason
from trusted_strategy_statistics_v1
order by
    case trusted_reason
        when 'identity_suspect' then 1
        when 'low_full_context_pct' then 2
        else 9
    end,
    trades desc;
"""

def remediation_action(reason: str) -> tuple[str, str]:
    if reason == "identity_suspect":
        return (
            "QUARANTINE_AND_REBUILD",
            "исключить_из_runtime_пересобрать_chains_attribution_statistics",
        )

    if reason == "low_full_context_pct":
        return (
            "ACCUMULATE_FULL_CONTEXT",
            "не_пересчитывать_в_runtime_копить_новые_full_context_сделки",
        )

    return (
        "MANUAL_REVIEW",
        "требуется_ручная_проверка_качества_данных",
    )

def main() -> int:
    print("=== ROOT CAUSE REMEDIATION PLAN V1 ===")
    print("mode=research_only")
    print("runtime_allow=0")
    print("execution_enabled=0")

    with psycopg2.connect(os.environ["DATABASE_URL"]) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(SQL)
            rows = cur.fetchall()

    quarantine = 0
    accumulate = 0
    review = 0

    for r in rows:
        action, reason = remediation_action(r["trusted_reason"])

        if action == "QUARANTINE_AND_REBUILD":
            quarantine += 1
        elif action == "ACCUMULATE_FULL_CONTEXT":
            accumulate += 1
        else:
            review += 1

        print(
            "REMEDIATION_ROW "
            f"symbol={r['symbol']} "
            f"strategy={r['strategy']} "
            f"timeframe={r['timeframe']} "
            f"source={r['trade_source']} "
            f"trades={r['trades']} "
            f"entry_days={r['entry_days']} "
            f"exit_days={r['exit_days']} "
            f"full_ctx_pct={r['full_ctx_pct']} "
            f"identity_status={r['identity_status']} "
            f"trusted_status={r['trusted_status']} "
            f"trusted_reason={r['trusted_reason']} "
            f"remediation_action={action} "
            f"remediation_reason={reason} "
            "runtime_allow=0 execution_enabled=0"
        )

    print(
        "ROOT_CAUSE_REMEDIATION_SUMMARY "
        f"total={len(rows)} "
        f"quarantine_and_rebuild={quarantine} "
        f"accumulate_full_context={accumulate} "
        f"manual_review={review} "
        "runtime_allow=0 execution_enabled=0"
    )

    print("ROOT_CAUSE_REMEDIATION_PLAN_V1_OK")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
