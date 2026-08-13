from __future__ import annotations

from dataclasses import dataclass

from marketcore.services.research.edge_search_target_descriptor_resolver_v1 import (
    resolve_target_descriptor_v1,
)
from marketcore.services.research.edge_search_variant_capacity_resolver_v1 import (
    resolve_variant_capacity_v1,
)


@dataclass(frozen=True)
class CapacityFeedbackSummaryV1:
    reserve_variants: int
    requested_variants: int
    effective_variants: int
    released_variants: int
    unallocated_reserve_variants: int
    allocation_targets: int


def build_capacity_feedback_v1(
    conn,
    *,
    allocations,
    reserve_variants: int,
) -> CapacityFeedbackSummaryV1:
    requested_total = 0
    effective_total = 0
    released_total = 0
    allocation_targets = 0

    for item, _weight, requested in allocations:
        requested = int(requested)
        allocation_targets += 1
        requested_total += requested

        descriptor = resolve_target_descriptor_v1(
            conn,
            symbol=item.symbol,
            research_family=item.research_family,
        )

        if descriptor.state != "RESOLVED":
            released_total += requested
            continue

        capacity = resolve_variant_capacity_v1(
            symbol=item.symbol,
            research_family=item.research_family,
            strategy=descriptor.strategy,
            side=descriptor.side,
            requested_variants=requested,
        )

        effective_total += capacity.effective_variants
        released_total += capacity.unused_variants

    unallocated = int(reserve_variants) - effective_total

    if effective_total < 0:
        raise RuntimeError("NEGATIVE_EFFECTIVE_RESEARCH_CAPACITY")

    if unallocated < 0:
        raise RuntimeError("RESEARCH_BUDGET_OVERALLOCATED")

    if effective_total + unallocated != int(reserve_variants):
        raise RuntimeError("RESEARCH_BUDGET_CONSERVATION_FAILED")

    return CapacityFeedbackSummaryV1(
        reserve_variants=int(reserve_variants),
        requested_variants=requested_total,
        effective_variants=effective_total,
        released_variants=released_total,
        unallocated_reserve_variants=unallocated,
        allocation_targets=allocation_targets,
    )
