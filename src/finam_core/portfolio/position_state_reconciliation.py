from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PositionStateInput:
    symbol: str
    broker_qty: float
    local_qty: float
    lifecycle_qty: float
    managed_qty: float


@dataclass(frozen=True)
class PositionStateReconciliationDecision:
    symbol: str
    display_name: str
    broker_qty: float
    local_qty: float
    lifecycle_qty: float
    managed_qty: float
    status: str
    severity: str
    reason: str


def reconcile_position_state(
    item: PositionStateInput,
    tolerance: float = 1e-9,
) -> PositionStateReconciliationDecision:
    broker = float(item.broker_qty)
    local = float(item.local_qty)
    lifecycle = float(item.lifecycle_qty)
    managed = float(item.managed_qty)

    def same(a: float, b: float) -> bool:
        return abs(a - b) <= tolerance

    if same(broker, local) and same(broker, lifecycle) and same(broker, managed):
        return PositionStateReconciliationDecision(
            symbol=item.symbol,
            display_name=item.symbol,
            broker_qty=broker,
            local_qty=local,
            lifecycle_qty=lifecycle,
            managed_qty=managed,
            status="OK",
            severity="INFO",
            reason="all_position_states_match",
        )

    if broker != 0.0 and local == 0.0:
        return PositionStateReconciliationDecision(
            symbol=item.symbol,
            display_name=item.symbol,
            broker_qty=broker,
            local_qty=local,
            lifecycle_qty=lifecycle,
            managed_qty=managed,
            status="BROKER_LOCAL_MISMATCH",
            severity="CRITICAL",
            reason="broker_position_exists_but_local_position_is_zero",
        )

    if broker != 0.0 and lifecycle == 0.0:
        return PositionStateReconciliationDecision(
            symbol=item.symbol,
            display_name=item.symbol,
            broker_qty=broker,
            local_qty=local,
            lifecycle_qty=lifecycle,
            managed_qty=managed,
            status="BROKER_LIFECYCLE_MISMATCH",
            severity="HIGH",
            reason="broker_position_exists_but_lifecycle_position_is_zero",
        )

    return PositionStateReconciliationDecision(
        symbol=item.symbol,
            display_name=item.symbol,
        broker_qty=broker,
        local_qty=local,
        lifecycle_qty=lifecycle,
        managed_qty=managed,
        status="MISMATCH",
        severity="HIGH",
        reason="position_states_are_not_equal",
    )
