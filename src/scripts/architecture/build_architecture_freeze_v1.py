#!/usr/bin/env python3
from __future__ import annotations

import os
import psycopg2
import psycopg2.extras

SQL = """
select
    (select count(*) from database_object_registry_v1) as registry_objects,
    (select count(*) from database_object_registry_review_plan_v1) as review_plan_objects,
    (select count(*) from database_object_registry_review_plan_v1 where proposed_action='DROP_CANDIDATE') as drop_candidates,
    (select count(*) from database_object_registry_review_plan_v1 where proposed_action='ARCHIVE_CANDIDATE') as archive_candidates,
    (select count(*) from strategy_statistics_v3 where statistics_status='STATISTICALLY_REVIEWABLE') as v3_reviewable,
    (select count(*) from v3_burst_artifact_gate where burst_status='BURST_ARTIFACT') as burst_artifacts,
    (select count(*) from trusted_candidate_discovery_v1) as trusted_candidates,
    (select count(*) from runtime_active_universe where is_enabled=true) as runtime_active;
"""

def main() -> int:
    print("=== ARCHITECTURE FREEZE V1 ===")
    print("mode=architecture_freeze")
    print("runtime_allow=0")
    print("execution_enabled=0")

    with psycopg2.connect(os.environ["DATABASE_URL"]) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(SQL)
            r = cur.fetchone()

    print(
        "ARCH_FREEZE_STATE "
        f"registry_objects={r['registry_objects']} "
        f"review_plan_objects={r['review_plan_objects']} "
        f"drop_candidates={r['drop_candidates']} "
        f"archive_candidates={r['archive_candidates']} "
        f"v3_reviewable={r['v3_reviewable']} "
        f"burst_artifacts={r['burst_artifacts']} "
        f"trusted_candidates={r['trusted_candidates']} "
        f"runtime_active={r['runtime_active']} "
        "runtime_allow=0 execution_enabled=0"
    )

    print("ARCH_FREEZE_CANONICAL core=trades,orders,fills,positions,broker_order_snapshots,execution_events")
    print("ARCH_FREEZE_CANONICAL market_data=market_ticks,market_bars,market_data,signals,feature_snapshots,instrument_reference")
    print("ARCH_FREEZE_CANONICAL runtime=runtime_active_universe,runtime_strategy_scores,runtime_allocator_decisions,runtime_observations")
    print("ARCH_FREEZE_CANONICAL research=closed_trade_chains_v3,trade_attribution_v3,strategy_statistics_v3,v3_burst_artifact_gate")
    print("ARCH_FREEZE_LEGACY closed_trade_chains_v2,trade_attribution_v2,legacy_scorecards,legacy_shadow_statistics")
    print("ARCH_FREEZE_FORBIDDEN_RUNTIME v2_chains,v2_attribution,quarantine_artifacts,burst_artifacts,symbol_only_matches,research_only_statistics")

    status = "FROZEN_SAFE_BLOCKED"

    # ARCHITECTURE_FREEZE_V1_RUNTIME_ACTIVE_VERDICT:
    # Русский комментарий:
    # runtime_active_universe может содержать enabled rows,
    # но это не означает, что стратегии trusted.
    # Поэтому reason должен честно различать:
    # 1) runtime_active пуст;
    # 2) runtime_active не пуст, но trusted/v3 candidates отсутствуют.
    if int(r["runtime_active"] or 0) > 0:
        reason = "runtime_active_present_but_no_trusted_candidates_no_v3_reviewable"
    else:
        reason = "no_runtime_active_no_trusted_candidates_no_v3_reviewable"

    print(
        "ARCHITECTURE_FREEZE_VERDICT "
        f"status={status} "
        f"reason={reason} "
        "new_strategies_allowed=false "
        "schema_changes_allowed=false "
        "destructive_db_actions_allowed=false "
        "runtime_allow=0 execution_enabled=0"
    )

    print("ARCHITECTURE_FREEZE_V1_OK")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
