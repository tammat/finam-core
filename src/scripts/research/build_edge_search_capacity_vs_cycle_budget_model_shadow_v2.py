"""Read-only shadow V2: universe capacity отдельно от cycle budget."""

from __future__ import annotations

import os
from dataclasses import dataclass

import psycopg2

from scripts.research.build_edge_search_research_budget_allocation_shadow_v1 import (
    build_allocations,
)
from marketcore.services.research.edge_search_target_descriptor_resolver_v1 import (
    resolve_target_descriptor_v1,
)
from marketcore.services.research.edge_search_variant_capacity_resolver_v1 import (
    resolve_variant_capacity_v1,
)


@dataclass(frozen=True)
class CapacityCycleBudgetV2:
    requested_capacity: int
    universe_capacity: int
    effective_universe_capacity: int
    cycle_budget: int
    remaining_unique_capacity: int


def resolve_capacity_cycle_budget_v2(
    *,
    requested_capacity: int,
    available_capacity: int,
    research_family: str,
) -> CapacityCycleBudgetV2:
    if requested_capacity <= 0:
        raise RuntimeError(
            "CAPACITY_VS_CYCLE_REQUESTED_CAPACITY_INVALID"
        )

    if available_capacity < 0:
        raise RuntimeError(
            "CAPACITY_VS_CYCLE_AVAILABLE_CAPACITY_INVALID"
        )

    effective = min(
        requested_capacity,
        available_capacity,
    )

    # Structural contract:
    # TARGETED EXIT_OOS evaluates exactly one frozen challenger per cycle.
    if research_family == "EXIT_OOS":
        cycle_budget = min(1, effective)
    else:
        # Для других families V2 не изобретает новую semantics.
        cycle_budget = effective

    remaining = max(
        effective - cycle_budget,
        0,
    )

    return CapacityCycleBudgetV2(
        requested_capacity=requested_capacity,
        universe_capacity=available_capacity,
        effective_universe_capacity=effective,
        cycle_budget=cycle_budget,
        remaining_unique_capacity=remaining,
    )


def main() -> int:
    _decisions, _eligible, allocations, _weight = build_allocations()

    rows = 0

    with psycopg2.connect(os.environ["DATABASE_URL"]) as conn:
        conn.set_session(readonly=True)

        for item, _weight, requested in allocations:
            descriptor = resolve_target_descriptor_v1(
                conn,
                symbol=item.symbol,
                research_family=item.research_family,
            )

            if descriptor.state != "RESOLVED":
                continue

            capacity = resolve_variant_capacity_v1(
                symbol=item.symbol,
                research_family=item.research_family,
                strategy=descriptor.strategy,
                side=descriptor.side,
                requested_variants=int(requested),
            )

            model = resolve_capacity_cycle_budget_v2(
                requested_capacity=int(requested),
                available_capacity=capacity.available_variants,
                research_family=item.research_family,
            )

            rows += 1

            print(
                "CAPACITY_VS_CYCLE_BUDGET "
                f"symbol={item.symbol} "
                f"family={item.research_family} "
                f"strategy={descriptor.strategy} "
                f"side={descriptor.side} "
                f"requested_capacity={model.requested_capacity} "
                f"universe_capacity={model.universe_capacity} "
                f"effective_universe_capacity="
                f"{model.effective_universe_capacity} "
                f"cycle_budget={model.cycle_budget} "
                f"remaining_unique_capacity="
                f"{model.remaining_unique_capacity}"
            )

    print(f"resolved_targets={rows}")
    print("cycle_budget_source=STRUCTURAL_TARGETED_CONTRACT")
    print("statistical_estimation_required=0")
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
        "EDGE_SEARCH_CAPACITY_VS_CYCLE_BUDGET_MODEL_SHADOW_V2_READY"
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
