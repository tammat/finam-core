from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ReconciliationIssue:
    severity: str
    category: str
    symbol: str
    reason: str


class PortfolioReconciliationEngine:
    """Русский комментарий: institutional reconciliation engine."""

    def check_position_vs_lifecycle(
        self,
        *,
        symbol: str,
        position_qty: float,
        lifecycle_qty: float,
    ) -> ReconciliationIssue | None:

        if abs(position_qty - lifecycle_qty) > 0.0001:
            return ReconciliationIssue(
                severity="HIGH",
                category="POSITION_LIFECYCLE_MISMATCH",
                symbol=symbol,
                reason=(
                    f"position_qty={position_qty};"
                    f"lifecycle_qty={lifecycle_qty}"
                ),
            )

        return None

    def check_execution_vs_position(
        self,
        *,
        symbol: str,
        executed_qty: float,
        position_qty: float,
    ) -> ReconciliationIssue | None:

        if abs(executed_qty - position_qty) > 0.0001:
            return ReconciliationIssue(
                severity="HIGH",
                category="EXECUTION_POSITION_MISMATCH",
                symbol=symbol,
                reason=(
                    f"executed_qty={executed_qty};"
                    f"position_qty={position_qty}"
                ),
            )

        return None

    def check_orphan_lifecycle(
        self,
        *,
        symbol: str,
        lifecycle_qty: float,
        position_exists: bool,
    ) -> ReconciliationIssue | None:

        if lifecycle_qty > 0 and not position_exists:
            return ReconciliationIssue(
                severity="MEDIUM",
                category="ORPHAN_LIFECYCLE",
                symbol=symbol,
                reason="lifecycle_exists_without_position",
            )

        return None

    def check_orphan_position(
        self,
        *,
        symbol: str,
        position_qty: float,
        lifecycle_exists: bool,
    ) -> ReconciliationIssue | None:

        if position_qty > 0 and not lifecycle_exists:
            return ReconciliationIssue(
                severity="MEDIUM",
                category="ORPHAN_POSITION",
                symbol=symbol,
                reason="position_exists_without_lifecycle",
            )

        return None
