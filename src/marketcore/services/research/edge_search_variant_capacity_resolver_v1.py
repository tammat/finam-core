from __future__ import annotations

from dataclasses import dataclass

from finam_core.analytics.entry_exit_optimizer import (
    default_variants,
    expert_shadow_variants,
)


@dataclass(frozen=True)
class VariantCapacityV1:
    symbol: str
    research_family: str
    strategy: str
    side: str
    requested_variants: int
    available_variants: int
    effective_variants: int
    unused_variants: int
    state: str
    reason: str


def resolve_variant_capacity_v1(
    *,
    symbol: str,
    research_family: str,
    strategy: str,
    side: str,
    requested_variants: int,
) -> VariantCapacityV1:
    if requested_variants <= 0:
        return VariantCapacityV1(
            symbol=symbol,
            research_family=research_family,
            strategy=strategy,
            side=side,
            requested_variants=requested_variants,
            available_variants=0,
            effective_variants=0,
            unused_variants=0,
            state="REJECTED",
            reason="NON_POSITIVE_REQUESTED_VARIANTS",
        )

    family = research_family.strip().upper()

    if family != "EXIT_OOS":
        return VariantCapacityV1(
            symbol=symbol,
            research_family=family,
            strategy=strategy,
            side=side,
            requested_variants=requested_variants,
            available_variants=requested_variants,
            effective_variants=requested_variants,
            unused_variants=0,
            state="PASSTHROUGH",
            reason="CAPACITY_RESOLVER_NOT_DEFINED_FOR_FAMILY",
        )

    universe = (
        tuple(default_variants(strategy))
        + tuple(expert_shadow_variants(strategy))
    )

    available = len(universe)
    effective = min(requested_variants, available)
    unused = requested_variants - effective

    return VariantCapacityV1(
        symbol=symbol,
        research_family=family,
        strategy=strategy,
        side=side,
        requested_variants=requested_variants,
        available_variants=available,
        effective_variants=effective,
        unused_variants=unused,
        state="RESOLVED",
        reason="DETERMINISTIC_VARIANT_UNIVERSE_CAPACITY",
    )
