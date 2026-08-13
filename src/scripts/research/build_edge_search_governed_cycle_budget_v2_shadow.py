"""Read-only comparison текущего variant budget и workflow-aware cycle budget."""

from __future__ import annotations

import os

import psycopg2
from psycopg2.extras import RealDictCursor

from finam_core.analytics.entry_exit_optimizer import (
    default_variants,
    expert_shadow_variants,
)


SYMBOL = "BRQ6@RTSX"
STRATEGY = "BR_CONSERVATIVE_BREAKOUT"
SIDE = "LONG"

ACTIVE_STAGES = {
    "SHADOW_ACCUMULATION",
    "V5_OOS_COLLECTING",
    "V5_OOS_PASS",
    "PAPER_MINIMAL_ACTIVE",
    "PAPER_MONITOR",
    "PAPER_CONTINUE",
}

TERMINAL_STAGES = {
    "REJECTED",
    "ROLLED_BACK",
    "EXPENSIVE_GATES_FAILED",
}


def main() -> int:
    universe = (
        tuple(default_variants(STRATEGY))
        + tuple(expert_shadow_variants(STRATEGY))
    )

    universe_codes = {
        variant.code
        for variant in universe
    }

    with psycopg2.connect(os.environ["DATABASE_URL"]) as conn:
        conn.set_session(readonly=True)

        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                SELECT
                    candidate_code,
                    workflow_stage
                FROM analytics.entry_exit_promotion_workflow_v1
                WHERE strategy_code=%s
                  AND side_code=%s
                """,
                (STRATEGY, SIDE),
            )

            rows = list(cur.fetchall())

            cur.execute(
                """
                SELECT ep.variant_budget
                FROM marketcore_action.command_request_v2 q
                JOIN marketcore_action.edge_search_request_parameter_v1 ep
                  ON ep.request_id=q.request_id
                WHERE q.target_id=%s
                  AND q.status='COMPLETED'
                ORDER BY q.finished_at DESC
                LIMIT 1
                """,
                (
                    "TARGETED_V1|EXIT_OOS|BRQ6@RTSX|"
                    "BR_CONSERVATIVE_BREAKOUT|LONG",
                ),
            )

            latest = cur.fetchone()

    if not latest:
        raise RuntimeError(
            "GOVERNED_CYCLE_BUDGET_REQUIRES_COMPLETED_REQUEST"
        )

    transported_variant_budget = int(
        latest["variant_budget"]
    )

    stage_by_code = {
        str(row["candidate_code"]): str(row["workflow_stage"])
        for row in rows
        if str(row["candidate_code"]) in universe_codes
    }

    terminal_codes = {
        code
        for code, stage in stage_by_code.items()
        if stage in TERMINAL_STAGES
    }

    active_codes = {
        code
        for code, stage in stage_by_code.items()
        if stage in ACTIVE_STAGES
    }

    unseen_codes = universe_codes - set(stage_by_code)

    consumable_codes = active_codes | unseen_codes

    physical_universe = len(universe_codes)
    consumable_capacity = len(consumable_codes)

    # Structural contract: один frozen challenger за targeted cycle.
    cycle_budget = min(1, consumable_capacity)

    excess_transport_capacity = max(
        transported_variant_budget - cycle_budget,
        0,
    )

    print(
        "GOVERNED_CYCLE_BUDGET_V2 "
        f"symbol={SYMBOL} "
        f"strategy={STRATEGY} "
        f"side={SIDE} "
        f"physical_universe={physical_universe} "
        f"terminal_candidates={len(terminal_codes)} "
        f"active_candidates={len(active_codes)} "
        f"unseen_candidates={len(unseen_codes)} "
        f"consumable_capacity={consumable_capacity} "
        f"transported_variant_budget="
        f"{transported_variant_budget} "
        f"proposed_cycle_budget={cycle_budget} "
        f"excess_transport_capacity="
        f"{excess_transport_capacity}"
    )

    for code in sorted(consumable_codes):
        print(
            "GOVERNED_CYCLE_CONSUMABLE "
            f"candidate={code} "
            f"stage={stage_by_code.get(code, 'UNSEEN')}"
        )

    assert physical_universe == (
        len(terminal_codes)
        + len(active_codes)
        + len(unseen_codes)
    )

    assert terminal_codes.isdisjoint(
        consumable_codes
    )

    assert cycle_budget <= consumable_capacity

    print("variant_budget_semantically_overloaded=1")
    print("universe_capacity_equals_cycle_budget=0")
    print("terminal_capacity_transport_required=0")
    print("cycle_budget_source=STRUCTURAL_TARGETED_CONTRACT")
    print("parameter_store_changed=0")
    print("worker_transport_changed=0")
    print("optimizer_changed=0")
    print("allocator_changed=0")
    print("db_writes_performed=0")
    print("queue_writes_performed=0")
    print("runtime_changed=0")
    print("execution_changed=0")
    print("orders_changed=0")
    print("fills_changed=0")
    print("micro_live_allowed=0")

    print(
        "VERDICT="
        "EDGE_SEARCH_GOVERNED_CYCLE_BUDGET_V2_SHADOW_READY"
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
