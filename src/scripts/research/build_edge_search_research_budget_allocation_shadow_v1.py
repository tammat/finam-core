"""Read-only shadow allocation резервного Edge Search research budget."""

from __future__ import annotations

from scripts.research.build_edge_search_research_budget_priority_v1 import (
    classify,
)
from marketcore.services.research.research_center_service import (
    ResearchCenterService,
)


RESERVE_VARIANTS = 40

PRIORITY_WEIGHTS = {
    "HIGH": 3,
    "MEDIUM_HIGH": 2,
}


def build_allocations():
    """Возвращает текущее shadow-распределение research budget без записей в БД."""
    frontier = ResearchCenterService().load().frontier

    decisions = tuple(
        classify(row)
        for row in frontier.rows[:5]
    )

    eligible = tuple(
        decision
        for decision in decisions
        if (
            decision.decision == "PRIORITIZE"
            and decision.priority in PRIORITY_WEIGHTS
        )
    )

    total_weight = sum(
        PRIORITY_WEIGHTS[item.priority]
        for item in eligible
    )

    allocations = []
    assigned = 0

    if total_weight > 0:
        for index, item in enumerate(eligible):
            weight = PRIORITY_WEIGHTS[item.priority]

            if index == len(eligible) - 1:
                variants = RESERVE_VARIANTS - assigned
            else:
                variants = (
                    RESERVE_VARIANTS * weight
                ) // total_weight

            assigned += variants

            allocations.append(
                (
                    item,
                    weight,
                    variants,
                )
            )

    return decisions, eligible, tuple(allocations), total_weight


def main() -> int:
    decisions, eligible, allocations, total_weight = build_allocations()

    if total_weight <= 0:
        print("eligible_cohorts=0")
        print(f"reserve_variants={RESERVE_VARIANTS}")
        print("assigned_variants_shadow=0")
        print(
            f"unallocated_variants_shadow="
            f"{RESERVE_VARIANTS}"
        )
        print("resource_allocation_changed=0")
        print("db_writes_performed=0")
        print(
            "VERDICT="
            "EDGE_SEARCH_RESEARCH_BUDGET_ALLOCATION_SHADOW_V1_READY"
        )
        return 0

    assigned = sum(
        variants
        for _item, _weight, variants in allocations
    )

    for item, weight, variants in allocations:
        print(
            "BUDGET_ALLOCATION_SHADOW_ROW "
            f"symbol={item.symbol} "
            f"research_family={item.research_family} "
            f"priority={item.priority} "
            f"weight={weight} "
            f"variants={variants} "
            f"reason={item.reason}"
        )

    blocked = tuple(
        item.symbol
        for item in decisions
        if item.decision == "BLOCK_LOCAL_GRID"
    )

    held = tuple(
        item.symbol
        for item in decisions
        if item.decision == "HOLD"
    )

    print(f"eligible_cohorts={len(eligible)}")
    print(f"total_priority_weight={total_weight}")
    print(f"reserve_variants={RESERVE_VARIANTS}")
    print(f"assigned_variants_shadow={assigned}")
    print(
        "unallocated_variants_shadow="
        f"{RESERVE_VARIANTS - assigned}"
    )
    print(
        "blocked_local_grid_symbols="
        + ",".join(blocked)
    )
    print(
        "held_symbols="
        + ",".join(held)
    )

    print("budget_assignment_changed=0")
    print("resource_allocation_changed=0")
    print("policy_changed=0")
    print("db_writes_performed=0")
    print("runtime_changed=0")
    print("execution_changed=0")
    print("orders_changed=0")
    print("fills_changed=0")
    print("micro_live_allowed=0")

    print(
        "VERDICT="
        "EDGE_SEARCH_RESEARCH_BUDGET_ALLOCATION_SHADOW_V1_READY"
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
