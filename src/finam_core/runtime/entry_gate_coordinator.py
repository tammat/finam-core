from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from finam_core.runtime.strategy_runtime_control_service import StrategyRuntimeControlService
from finam_core.runtime.trade_gate_service import TradeGateService
from finam_core.runtime.trend_gate_service import TrendGateService


@dataclass(frozen=True)
class EntryGateDecision:
    """Русский комментарий: единый результат проверки entry-gates."""
    allowed: bool
    qty: float
    reason: str
    gate: str


class EntryGateCoordinator:
    """
    Русский комментарий:
    Координатор входных gate-фильтров.

    Порядок:
    1) trend;
    2) cooldown;
    3) trade limit;
    4) runtime-control.
    """

    def __init__(
        self,
        trade_gate_service: TradeGateService,
        runtime_control_service: StrategyRuntimeControlService | Any,
        trend_gate_service: TrendGateService,
    ) -> None:
        self.trade_gate_service = trade_gate_service
        self.runtime_control_service = runtime_control_service
        self.trend_gate_service = trend_gate_service

    def allow_entry(
        self,
        symbol: str,
        strategy: str,
        strategy_side: str,
        expected_side: str | None,
        qty: float,
        price: float,
        atr: float | None = None,
    ) -> EntryGateDecision:
        trend = self.trend_gate_service.allow_entry(
            symbol=symbol,
            side=strategy_side,
            expected_side=expected_side,
        )

        if not trend.allowed:
            return EntryGateDecision(False, 0.0, trend.reason, "trend")

        cooldown = self.trade_gate_service.cooldown_allows(
            symbol=symbol,
            price=price,
            atr=atr,
        )

        if not cooldown.allowed:
            return EntryGateDecision(False, 0.0, cooldown.reason, "trade_cooldown")

        limit = self.trade_gate_service.trade_limit_allows(symbol)

        if not limit.allowed:
            return EntryGateDecision(False, 0.0, limit.reason, "trade_limit")

        runtime_allowed, adjusted_qty, runtime_reason = self.runtime_control_service.allow_paper(
            symbol=symbol,
            qty=qty,
            strategy=strategy,
        )

        if not runtime_allowed:
            return EntryGateDecision(False, 0.0, runtime_reason, "runtime_control")

        self.trade_gate_service.account_trade(symbol)

        return EntryGateDecision(True, float(adjusted_qty), runtime_reason, "allow")
