from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class PositionRecoveryIssue:
    symbol: str
    kind: str
    broker_qty: float
    local_qty: float
    message: str


@dataclass(frozen=True)
class PositionRecoveryDecision:
    allowed: bool
    reason: str
    issues: list[PositionRecoveryIssue] = field(default_factory=list)


class PositionRecoveryService:
    """Русский комментарий: сверяет broker positions и local managed positions после restart."""

    def __init__(
        self,
        *,
        positions_client: Any,
        managed_service: Any,
        qty_tolerance: float = 0.000001,
    ) -> None:
        self.positions_client = positions_client
        self.managed_service = managed_service
        self.qty_tolerance = float(qty_tolerance)

    def _load_broker_positions(self) -> dict[str, float]:
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

    def _load_local_positions(self) -> dict[str, float]:
        repo = getattr(self.managed_service, "repository", None)
        if repo is None or not hasattr(repo, "list_all"):
            return {}

        result: dict[str, float] = {}

        for p in repo.list_all() or []:
            if isinstance(p, dict):
                symbol = str(p.get("symbol") or p.get("ticker") or "")
                qty = float(p.get("qty") or p.get("quantity") or 0.0)
            else:
                symbol = str(getattr(p, "symbol", None) or getattr(p, "ticker", None) or "")
                qty = float(getattr(p, "qty", None) or getattr(p, "quantity", None) or 0.0)

            if symbol:
                result[symbol] = qty

        return result

    def check(self) -> PositionRecoveryDecision:
        broker_positions = self._load_broker_positions()
        local_positions = self._load_local_positions()

        issues: list[PositionRecoveryIssue] = []

        all_symbols = set(broker_positions) | set(local_positions)

        for symbol in sorted(all_symbols):
            broker_qty = float(broker_positions.get(symbol, 0.0))
            local_qty = float(local_positions.get(symbol, 0.0))

            if abs(broker_qty - local_qty) <= self.qty_tolerance:
                continue

            if symbol in broker_positions and symbol not in local_positions:
                kind = "broker_position_missing_locally"
                message = "broker has position but local managed state is missing"
            elif symbol not in broker_positions and symbol in local_positions:
                kind = "local_position_missing_at_broker"
                message = "local managed state has position but broker does not"
            else:
                kind = "broker_local_qty_mismatch"
                message = "broker and local quantities differ"

            issues.append(
                PositionRecoveryIssue(
                    symbol=symbol,
                    kind=kind,
                    broker_qty=broker_qty,
                    local_qty=local_qty,
                    message=message,
                )
            )

        if issues:
            return PositionRecoveryDecision(
                allowed=False,
                reason="position_recovery_freeze",
                issues=issues,
            )

        return PositionRecoveryDecision(
            allowed=True,
            reason="position_recovery_ok",
            issues=[],
        )
