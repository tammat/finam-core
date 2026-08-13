"""Read-only shadow фактически consumable targeted challenger capacity."""

from __future__ import annotations

import os
from dataclasses import dataclass

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


@dataclass(frozen=True)
class ConsumableCapacityV1:
    universe_capacity: int
    observed_workflow_candidates: int
    terminal_candidates: int
    active_candidates: int
    unseen_candidates: int
    consumable_candidates: int
    cycle_budget: int


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

    unseen_codes = (
        universe_codes
        - set(stage_by_code)
    )

    # Consumable = active challenger + unseen candidates.
    # Terminal candidates исключены.
    consumable_codes = (
        active_codes
        | unseen_codes
    )

    model = ConsumableCapacityV1(
        universe_capacity=len(universe_codes),
        observed_workflow_candidates=len(stage_by_code),
        terminal_candidates=len(terminal_codes),
        active_candidates=len(active_codes),
        unseen_candidates=len(unseen_codes),
        consumable_candidates=len(consumable_codes),
        cycle_budget=min(1, len(consumable_codes)),
    )

    print(
        "CONSUMABLE_CAPACITY "
        f"symbol={SYMBOL} "
        f"strategy={STRATEGY} "
        f"side={SIDE} "
        f"universe_capacity={model.universe_capacity} "
        f"observed_workflow_candidates="
        f"{model.observed_workflow_candidates} "
        f"terminal_candidates={model.terminal_candidates} "
        f"active_candidates={model.active_candidates} "
        f"unseen_candidates={model.unseen_candidates} "
        f"consumable_candidates={model.consumable_candidates} "
        f"cycle_budget={model.cycle_budget}"
    )

    for code in sorted(active_codes):
        print(
            "CONSUMABLE_ACTIVE "
            f"candidate={code} "
            f"stage={stage_by_code[code]}"
        )

    for code in sorted(unseen_codes):
        print(
            "CONSUMABLE_UNSEEN "
            f"candidate={code}"
        )

    assert model.universe_capacity == (
        model.terminal_candidates
        + model.active_candidates
        + model.unseen_candidates
    )

    assert terminal_codes.isdisjoint(
        consumable_codes
    )

    print("physical_universe_equals_consumable_capacity=0")
    print("terminal_candidates_consumable=0")
    print("cycle_budget_source=STRUCTURAL_TARGETED_CONTRACT")
    print("capacity_conservation_ok=1")

    print("allocator_changed=0")
    print("budget_transport_changed=0")
    print("optimizer_changed=0")
    print("db_writes_performed=0")
    print("queue_writes_performed=0")
    print("runtime_changed=0")
    print("execution_changed=0")
    print("orders_changed=0")
    print("fills_changed=0")
    print("micro_live_allowed=0")

    print(
        "VERDICT="
        "EDGE_SEARCH_CONSUMABLE_CHALLENGER_CAPACITY_SHADOW_V1_READY"
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
