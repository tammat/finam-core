from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class LifecycleStalePositionInput:
    symbol: str
    display_name: str
    broker_qty: float
    lifecycle_qty: float
    managed_qty: float
    reconciliation_status: str


@dataclass(frozen=True)
class LifecycleStalePositionAdvice:
    symbol: str
    display_name: str
    action: str
    severity: str
    block_new_entries: bool
    reason: str


def build_lifecycle_stale_position_advice(
    item: LifecycleStalePositionInput,
) -> LifecycleStalePositionAdvice:
    broker = float(item.broker_qty)
    lifecycle = float(item.lifecycle_qty)
    managed = float(item.managed_qty)

    if broker != 0.0 and lifecycle == 0.0:
        return LifecycleStalePositionAdvice(
            symbol=item.symbol,
            display_name=item.display_name,
            action="REBUILD_LIFECYCLE_STATE",
            severity="HIGH",
            block_new_entries=True,
            reason="broker_position_exists_but_lifecycle_state_missing",
        )

    if broker == 0.0 and lifecycle != 0.0:
        return LifecycleStalePositionAdvice(
            symbol=item.symbol,
            display_name=item.display_name,
            action="IGNORE_OR_CLEAN_STALE_LIFECYCLE",
            severity="MEDIUM",
            block_new_entries=False,
            reason="lifecycle_state_exists_but_broker_position_is_zero",
        )

    if broker != lifecycle:
        return LifecycleStalePositionAdvice(
            symbol=item.symbol,
            display_name=item.display_name,
            action="SYNC_LIFECYCLE_QTY",
            severity="HIGH",
            block_new_entries=True,
            reason="broker_and_lifecycle_quantities_are_different",
        )

    if managed != 0.0 and broker == lifecycle:
        return LifecycleStalePositionAdvice(
            symbol=item.symbol,
            display_name=item.display_name,
            action="CONFIRMED",
            severity="INFO",
            block_new_entries=False,
            reason="broker_lifecycle_and_managed_state_are_consistent",
        )

    return LifecycleStalePositionAdvice(
        symbol=item.symbol,
        display_name=item.display_name,
        action="NO_ACTION",
        severity="INFO",
        block_new_entries=False,
        reason="no_lifecycle_stale_condition",
    )
