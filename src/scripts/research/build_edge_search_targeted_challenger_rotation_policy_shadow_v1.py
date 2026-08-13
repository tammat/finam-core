"""Read-only shadow policy targeted challenger rotation."""

from __future__ import annotations

import hashlib
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

    by_code = {
        variant.code: variant
        for variant in universe
    }

    with psycopg2.connect(os.environ["DATABASE_URL"]) as conn:
        conn.set_session(readonly=True)

        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                SELECT
                    candidate_code,
                    workflow_stage,
                    first_entered_at
                FROM analytics.entry_exit_promotion_workflow_v1
                WHERE strategy_code=%s
                  AND side_code=%s
                ORDER BY first_entered_at,candidate_code
                """,
                (STRATEGY, SIDE),
            )

            workflow = list(cur.fetchall())

    stage_by_code = {
        str(row["candidate_code"]): str(row["workflow_stage"])
        for row in workflow
    }

    active = [
        code
        for code, stage in stage_by_code.items()
        if stage in ACTIVE_STAGES
        and code in by_code
    ]

    if active:
        active.sort()
        selected_code = active[0]
        decision = "KEEP_ACTIVE"
    else:
        available = [
            variant
            for variant in universe
            if stage_by_code.get(variant.code) not in TERMINAL_STAGES
        ]

        if not available:
            raise RuntimeError(
                "TARGETED_ROTATION_NO_NON_TERMINAL_CANDIDATE"
            )

        digest = hashlib.sha256(
            (
                f"{STRATEGY}|{SYMBOL}|{SIDE}|"
                "TARGETED_ROTATION_POLICY_V1"
            ).encode()
        ).digest()

        index = (
            int.from_bytes(digest[:4], "big")
            % len(available)
        )

        selected_code = available[index].code
        decision = "SELECT_NEXT_NON_TERMINAL"

    selected_stage = stage_by_code.get(
        selected_code,
        "UNSEEN",
    )

    selected_terminal = (
        selected_stage in TERMINAL_STAGES
    )

    terminal_count = sum(
        1
        for stage in stage_by_code.values()
        if stage in TERMINAL_STAGES
    )

    non_terminal_count = sum(
        1
        for variant in universe
        if stage_by_code.get(variant.code)
        not in TERMINAL_STAGES
    )

    print(f"universe_size={len(universe)}")
    print(f"terminal_candidates={terminal_count}")
    print(f"non_terminal_candidates={non_terminal_count}")
    print(f"active_candidates={len(active)}")
    print(f"rotation_decision={decision}")
    print(f"proposed_candidate={selected_code}")
    print(f"proposed_candidate_stage={selected_stage}")
    print(f"proposed_candidate_terminal={int(selected_terminal)}")

    assert not selected_terminal

    print("terminal_candidate_reselection_allowed=0")
    print("active_candidate_stability_preserved=1")
    print("one_challenger_per_cycle_preserved=1")
    print("deterministic_selection_preserved=1")

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
        "EDGE_SEARCH_TARGETED_CHALLENGER_ROTATION_POLICY_SHADOW_V1_READY"
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
