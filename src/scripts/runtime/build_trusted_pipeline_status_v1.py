#!/usr/bin/env python3
from __future__ import annotations

import os
import psycopg2
import psycopg2.extras

QUERIES = {
    "identity_governance": """
        select count(*) from strategy_identity_governance_v1
    """,
    "trusted_statistics": """
        select count(*) from trusted_strategy_statistics_v1
        where trusted_status='TRUSTED'
    """,
    "trusted_candidates": """
        select count(*) from trusted_candidate_discovery_v1
    """,
    "runtime_gate_open": """
        select count(*) from trusted_runtime_gate_v1
        where gate_status='OPEN'
    """,
    "promotion_feed_open": """
        select count(*) from strategy_promotion_runtime_feed
        where coalesce(allow_paper_signal,false)=true
           or coalesce(allow_real_suggestion,false)=true
    """,
    "runtime_active_universe": """
        select count(*)
        from runtime_active_universe
        where coalesce(is_enabled,true)=true
    """
}

def scalar(cur, sql):
    try:
        cur.execute(sql)
        row = cur.fetchone()
        return int(row[0] or 0)
    except Exception:
        return -1

def main() -> int:
    print("=== TRUSTED PIPELINE STATUS V1 ===")
    print("mode=diagnostic")
    print("runtime_allow=0")
    print("execution_enabled=0")

    with psycopg2.connect(os.environ["DATABASE_URL"]) as conn:
        with conn.cursor() as cur:
            stats = {
                name: scalar(cur, sql)
                for name, sql in QUERIES.items()
            }

    for k, v in stats.items():
        print(f"PIPELINE_COMPONENT component={k} rows={v}")

    trusted = stats["trusted_statistics"]
    candidates = stats["trusted_candidates"]
    gate_open = stats["runtime_gate_open"]
    promotion_open = stats["promotion_feed_open"]

    if trusted == 0 and candidates == 0 and gate_open == 0 and promotion_open == 0:
        status = "SAFE_BLOCKED"
        reason = "no_trusted_candidates"
    elif trusted > 0 and candidates > 0 and gate_open > 0:
        status = "READY_FOR_REVIEW"
        reason = "trusted_candidates_exist"
    else:
        status = "INCONSISTENT"
        reason = "pipeline_state_mismatch"

    print(
        "PIPELINE_STATUS "
        f"status={status} "
        f"reason={reason} "
        f"trusted={trusted} "
        f"candidates={candidates} "
        f"gate_open={gate_open} "
        f"promotion_open={promotion_open}"
    )

    print("TRUSTED_PIPELINE_STATUS_V1_OK")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
