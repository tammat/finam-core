from __future__ import annotations

from dataclasses import dataclass

from finam_core.execution.managed_position_service import ManagedPositionService
from finam_core.portfolio.latest_real_positions_provider import LatestRealPositionsProvider


@dataclass(frozen=True)
class ReconciliationIssue:
    symbol: str
    kind: str
    broker_qty: float | None
    managed_qty: float | None
    message: str


class ManagedPositionReconciliation:
    def __init__(self, provider=None, managed=None):
        self.provider = provider or LatestRealPositionsProvider()
        self.managed = managed or ManagedPositionService()

    def check(self) -> list[ReconciliationIssue]:
        broker = {p.symbol: p for p in self.provider.get_positions()}
        managed = {p.symbol: p for p in self.managed.repository.list_all()}

        issues: list[ReconciliationIssue] = []

        for symbol, bp in broker.items():
            mp = managed.get(symbol)
            broker_qty_abs = abs(float(bp.qty))

            if mp is None:
                issues.append(ReconciliationIssue(
                    symbol=symbol,
                    kind="missing_managed",
                    broker_qty=float(bp.qty),
                    managed_qty=None,
                    message="Broker position exists but managed position is missing",
                ))
                continue

            if abs(float(mp.qty) - broker_qty_abs) > 1e-9:
                issues.append(ReconciliationIssue(
                    symbol=symbol,
                    kind="qty_mismatch",
                    broker_qty=float(bp.qty),
                    managed_qty=float(mp.qty),
                    message="Managed qty differs from broker qty",
                ))

            expected_side = "LONG" if float(bp.qty) > 0 else "SHORT"
            if mp.side.upper() != expected_side:
                issues.append(ReconciliationIssue(
                    symbol=symbol,
                    kind="side_mismatch",
                    broker_qty=float(bp.qty),
                    managed_qty=float(mp.qty),
                    message=f"Managed side differs from broker side: expected {expected_side}",
                ))

        for symbol, mp in managed.items():
            if symbol not in broker:
                issues.append(ReconciliationIssue(
                    symbol=symbol,
                    kind="stale_managed",
                    broker_qty=None,
                    managed_qty=float(mp.qty),
                    message="Managed position exists but broker position is missing",
                ))

        return issues
