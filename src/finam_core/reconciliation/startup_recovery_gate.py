from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from finam_core.reconciliation.active_orders_reconciliation import ActiveOrdersReconciliation


@dataclass(frozen=True)
class StartupRecoveryDecision:
    allowed: bool
    reason: str
    issues: list[str] = field(default_factory=list)


class StartupRecoveryGate:
    """Русский комментарий: startup gate перед разрешением исполнения после рестарта."""

    def __init__(
        self,
        *,
        orders_client: Any,
        managed_service: Any,
        positions_client: Any | None = None,
        oms_journal: Any | None = None,
        qty_tolerance: float = 0.000001,
    ) -> None:
        self.orders_client = orders_client
        self.managed_service = managed_service
        self.positions_client = positions_client
        self.oms_journal = oms_journal
        self.qty_tolerance = float(qty_tolerance)

    def _load_broker_positions(self) -> dict[str, float]:
        if self.positions_client is None:
            return {}

        if hasattr(self.positions_client, "get_positions"):
            positions = self.positions_client.get_positions()
        elif hasattr(self.positions_client, "list_positions"):
            positions = self.positions_client.list_positions()
        else:
            return {}

        result: dict[str, float] = {}
        for p in positions or []:
            if isinstance(p, dict):
                symbol = str(p.get("symbol") or p.get("ticker") or "")
                qty = float(p.get("qty") or p.get("quantity") or 0.0)
            else:
                symbol = str(getattr(p, "symbol", None) or getattr(p, "ticker", None) or "")
                qty = float(getattr(p, "qty", None) or getattr(p, "quantity", None) or 0.0)

            if symbol:
                result[symbol] = qty

        return result

    def _load_local_managed_positions(self) -> dict[str, float]:
        repo = getattr(self.managed_service, "repository", None)
        if repo is None or not hasattr(repo, "list_all"):
            return {}

        result: dict[str, float] = {}
        for p in repo.list_all() or []:
            symbol = str(getattr(p, "symbol", None) or "")
            qty = float(getattr(p, "qty", None) or getattr(p, "quantity", None) or 0.0)
            if symbol:
                result[symbol] = qty

        return result

    def check(self) -> StartupRecoveryDecision:
        issues: list[str] = []

        recon = ActiveOrdersReconciliation(
            orders_client=self.orders_client,
            managed_service=self.managed_service,
            oms_journal=self.oms_journal,
        )

        active_order_issues = recon.check()
        for issue in active_order_issues:
            issues.append(f"{issue.kind}:{issue.symbol}:{issue.message}")

        broker_positions = self._load_broker_positions()
        local_positions = self._load_local_managed_positions()

        for symbol, broker_qty in broker_positions.items():
            local_qty = local_positions.get(symbol, 0.0)
            if abs(float(broker_qty) - float(local_qty)) > self.qty_tolerance:
                issues.append(
                    f"broker_local_qty_mismatch:{symbol}:broker={broker_qty}:local={local_qty}"
                )

        for symbol, local_qty in local_positions.items():
            if symbol not in broker_positions and abs(float(local_qty)) > self.qty_tolerance:
                issues.append(
                    f"local_position_missing_at_broker:{symbol}:local={local_qty}"
                )

        if issues:
            return StartupRecoveryDecision(
                allowed=False,
                reason="startup_recovery_freeze",
                issues=issues,
            )

        return StartupRecoveryDecision(
            allowed=True,
            reason="startup_recovery_ok",
            issues=[],
        )
