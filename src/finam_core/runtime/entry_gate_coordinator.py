from __future__ import annotations

from dataclasses import dataclass

from finam_core.runtime.trade_gate_service import TradeGateService
from finam_core.runtime.strategy_runtime_control_service import (
    StrategyRuntimeControlService,
)
from finam_core.runtime.trend_gate_service import TrendGateService


@dataclass(frozen=True)
class EntryGateDecision:
    allowed: bool
    qty: float
    reason: str
    gate: str



class EntryGateCoordinator:
    """
    Русский комментарий:
    Единый orchestration layer для всех entry gates.
    """

    def __init__(
        self,
        runtime_control_service,
        trade_gate_service,
        trend_gate_service,
    ) -> None:
        self.runtime_control_service = runtime_control_service
        self.trade_gate_service = trade_gate_service
        self.trend_gate_service = trend_gate_service

    def allow_entry(
        self,
        symbol: str,
        strategy: str,
        strategy_side: str,
        qty: float,
        expected_side: str | None = None,
        atr: float | None = None,
    ):

        trend = self.trend_gate_service.allow_entry(
            symbol=symbol,
            side=strategy_side,
            expected_side=expected_side,
        )

        if not trend.allowed:
            return {
                "allowed": False,
                "qty": 0.0,
                "reason": trend.reason,
                "gate": "trend",
            }

        cooldown = self.trade_gate_service.cooldown_allows(
            symbol=symbol,
            atr=atr,
        )

        if not cooldown.allowed:
            return {
                "allowed": False,
                "qty": 0.0,
                "reason": cooldown.reason,
                "gate": "cooldown",
            }

        runtime = self.runtime_control_service.allow_entry(
            symbol=symbol,
            strategy=strategy,
            qty=qty,
        )

        if not runtime.allowed:
            return {
                "allowed": False,
                "qty": 0.0,
                "reason": runtime.reason,
                "gate": "runtime_control",
            }

        return {
            "allowed": True,
            "qty": runtime.qty,
            "reason": runtime.reason,
            "gate": "runtime_control",
        }

