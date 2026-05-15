from __future__ import annotations

from dataclasses import dataclass

from finam_core.runtime.trade_gate_service import TradeGateService
from finam_core.runtime.strategy_runtime_control_service import (
    StrategyRuntimeControlService,
)


@dataclass(frozen=True)
class EntryGateDecision:
    allowed: bool
    qty: float
    reason: str
    gate: str


class EntryGateCoordinator:
    """
    Русский комментарий:
    Единый orchestration-layer для entry gating.

    Этап 1:
    - trade cooldown;
    - trade limits;
    - runtime-control.

    TrendGateService подключим следующим extraction.
    """

    def __init__(
        self,
        trade_gate_service: TradeGateService,
        runtime_control_service: StrategyRuntimeControlService,
    ) -> None:
        self.trade_gate_service = trade_gate_service
        self.runtime_control_service = runtime_control_service

    def allow_entry(
        self,
        symbol: str,
        strategy: str,
        qty: float,
        price: float,
        atr: float | None = None,
    ) -> EntryGateDecision:

        cooldown = self.trade_gate_service.cooldown_allows(
            symbol=symbol,
            price=price,
            atr=atr,
        )

        if not cooldown.allowed:
            return EntryGateDecision(
                allowed=False,
                qty=0.0,
                reason=cooldown.reason,
                gate="trade_cooldown",
            )

        limit = self.trade_gate_service.trade_limit_allows(symbol)

        if not limit.allowed:
            return EntryGateDecision(
                allowed=False,
                qty=0.0,
                reason=limit.reason,
                gate="trade_limit",
            )

        runtime_allowed, adjusted_qty, runtime_reason = (
            self.runtime_control_service.allow_paper(
                symbol=symbol,
                qty=qty,
                strategy=strategy,
            )
        )

        if not runtime_allowed:
            return EntryGateDecision(
                allowed=False,
                qty=0.0,
                reason=runtime_reason,
                gate="runtime_control",
            )

        self.trade_gate_service.account_trade(symbol)

        return EntryGateDecision(
            allowed=True,
            qty=float(adjusted_qty),
            reason=runtime_reason,
            gate="allow",
        )
