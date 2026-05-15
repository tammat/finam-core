from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class StrategyRuntimeGateDecision:
    allowed: bool
    watch_only: bool
    original_qty: float
    adjusted_qty: float
    risk_multiplier: float
    status: str
    reason: str


class StrategyRuntimeGate:
    """Русский комментарий: применяет strategy_runtime_control перед исполнением заявки."""

    def __init__(self, repository: Any | None = None) -> None:
        self.repository = repository

    def evaluate(self, intent: dict[str, Any]) -> StrategyRuntimeGateDecision:
        symbol = str(intent.get("symbol") or "")
        strategy = str(
            intent.get("strategy")
            or (intent.get("features") or {}).get("strategy")
            or "default"
        )
        original_qty = float(intent.get("qty") or 0.0)

        if self.repository is None:
            return StrategyRuntimeGateDecision(
                allowed=True,
                watch_only=False,
                original_qty=original_qty,
                adjusted_qty=original_qty,
                risk_multiplier=1.0,
                status="NO_REPOSITORY",
                reason="Репозиторий runtime-control не подключён",
            )

        decision = self.repository.get_decision(symbol, strategy)

        allow_trade = bool(getattr(decision, "allow_trade", False))
        watch_only = bool(getattr(decision, "watch_only", True))
        risk_multiplier = float(getattr(decision, "risk_multiplier", 0.0) or 0.0)
        status = str(getattr(decision, "status", "UNKNOWN") or "UNKNOWN")
        reason = str(getattr(decision, "reason", "") or "")

        if not allow_trade or watch_only or risk_multiplier <= 0:
            return StrategyRuntimeGateDecision(
                allowed=False,
                watch_only=watch_only,
                original_qty=original_qty,
                adjusted_qty=0.0,
                risk_multiplier=risk_multiplier,
                status=status,
                reason=reason or "Стратегия заблокирована runtime-control",
            )

        adjusted_qty = round(original_qty * risk_multiplier, 8)

        if adjusted_qty <= 0:
            return StrategyRuntimeGateDecision(
                allowed=False,
                watch_only=watch_only,
                original_qty=original_qty,
                adjusted_qty=0.0,
                risk_multiplier=risk_multiplier,
                status=status,
                reason="После применения risk_multiplier размер заявки стал нулевым",
            )

        return StrategyRuntimeGateDecision(
            allowed=True,
            watch_only=watch_only,
            original_qty=original_qty,
            adjusted_qty=adjusted_qty,
            risk_multiplier=risk_multiplier,
            status=status,
            reason=reason or "Стратегия разрешена runtime-control",
        )
