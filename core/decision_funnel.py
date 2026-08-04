from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import StrEnum
from types import MappingProxyType
from typing import Any, Mapping
from uuid import UUID, uuid4


class DecisionStage(StrEnum):
    """Стадии прохождения торгового решения."""

    MARKET_DATA = "MARKET_DATA"
    STRATEGY = "STRATEGY"
    REGIME = "REGIME"
    EDGE = "EDGE"
    RISK = "RISK"
    PORTFOLIO = "PORTFOLIO"
    RUNTIME = "RUNTIME"
    EXECUTION = "EXECUTION"
    BROKER = "BROKER"
    FILL = "FILL"


class DecisionOutcome(StrEnum):
    """Результат проверки на отдельной стадии."""

    PASS = "PASS"
    REJECT = "REJECT"
    ERROR = "ERROR"
    SKIP = "SKIP"


class DecisionReason(StrEnum):
    """Нормализованные причины прохождения или отказа."""

    PASSED = "PASSED"

    # Market Data
    DATA_MISSING = "DATA_MISSING"
    DATA_STALE = "DATA_STALE"
    DATA_INVALID = "DATA_INVALID"

    # Strategy
    NO_SIGNAL = "NO_SIGNAL"
    STRATEGY_DISABLED = "STRATEGY_DISABLED"
    STRATEGY_ERROR = "STRATEGY_ERROR"

    # Regime
    REGIME_NOT_ALLOWED = "REGIME_NOT_ALLOWED"
    REGIME_UNKNOWN = "REGIME_UNKNOWN"

    # Edge
    EDGE_NOT_CONFIRMED = "EDGE_NOT_CONFIRMED"
    EDGE_SCORE_TOO_LOW = "EDGE_SCORE_TOO_LOW"
    CONFIDENCE_TOO_LOW = "CONFIDENCE_TOO_LOW"
    SAMPLE_TOO_SMALL = "SAMPLE_TOO_SMALL"

    # Risk
    MAX_RISK_PER_TRADE = "MAX_RISK_PER_TRADE"
    DAILY_LOSS_LIMIT = "DAILY_LOSS_LIMIT"
    EXPOSURE_LIMIT = "EXPOSURE_LIMIT"
    CORRELATION_FILTER = "CORRELATION_FILTER"
    KILL_SWITCH = "KILL_SWITCH"
    STOP_DISTANCE_INVALID = "STOP_DISTANCE_INVALID"

    # Portfolio
    POSITION_ALREADY_OPEN = "POSITION_ALREADY_OPEN"
    PORTFOLIO_LIMIT = "PORTFOLIO_LIMIT"
    INSUFFICIENT_CAPITAL = "INSUFFICIENT_CAPITAL"

    # Runtime
    RUNTIME_NOT_ALLOWED = "RUNTIME_NOT_ALLOWED"
    SHADOW_ONLY = "SHADOW_ONLY"
    PAPER_ONLY = "PAPER_ONLY"
    MICRO_LIVE_NOT_ALLOWED = "MICRO_LIVE_NOT_ALLOWED"
    MARKET_CLOSED = "MARKET_CLOSED"

    # Execution / broker / fill
    EXECUTION_DISABLED = "EXECUTION_DISABLED"
    ORDER_BUILD_ERROR = "ORDER_BUILD_ERROR"
    ORDER_REJECTED = "ORDER_REJECTED"
    BROKER_UNAVAILABLE = "BROKER_UNAVAILABLE"
    BROKER_REJECTED = "BROKER_REJECTED"
    FILL_TIMEOUT = "FILL_TIMEOUT"
    PARTIAL_FILL = "PARTIAL_FILL"

    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True, slots=True)
class SignalDecisionEvent:
    """
    Неизменяемое событие прохождения сигнала через Decision Funnel.

    AI-слой может формировать features и рекомендации, но не может
    создавать события EXECUTION/BROKER/FILL как источник торгового приказа.
    """

    signal_id: str
    symbol: str
    strategy: str
    timeframe: str
    stage: DecisionStage
    outcome: DecisionOutcome
    reason: DecisionReason

    event_id: UUID = field(default_factory=uuid4)
    occurred_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )

    direction: str | None = None
    attempt_no: int = 1
    source: str = "TRADING_ENGINE"
    context: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.signal_id.strip():
            raise ValueError("signal_id must not be empty")

        if not self.symbol.strip():
            raise ValueError("symbol must not be empty")

        if not self.strategy.strip():
            raise ValueError("strategy must not be empty")

        if not self.timeframe.strip():
            raise ValueError("timeframe must not be empty")

        if self.attempt_no < 1:
            raise ValueError("attempt_no must be greater than zero")

        if self.occurred_at.tzinfo is None:
            raise ValueError("occurred_at must be timezone-aware")

        if (
            self.outcome == DecisionOutcome.PASS
            and self.reason != DecisionReason.PASSED
        ):
            raise ValueError(
                "PASS outcome requires PASSED reason"
            )

        if (
            self.outcome == DecisionOutcome.REJECT
            and self.reason == DecisionReason.PASSED
        ):
            raise ValueError(
                "REJECT outcome cannot use PASSED reason"
            )

        normalized_context = MappingProxyType(dict(self.context))
        object.__setattr__(self, "context", normalized_context)


@dataclass(frozen=True, slots=True)
class FunnelDecision:
    """Результат проверки, удобный для подключения к существующим guards."""

    allowed: bool
    reason: DecisionReason
    context: Mapping[str, Any] = field(default_factory=dict)

    @property
    def outcome(self) -> DecisionOutcome:
        return (
            DecisionOutcome.PASS
            if self.allowed
            else DecisionOutcome.REJECT
        )

    def to_event(
        self,
        *,
        signal_id: str,
        symbol: str,
        strategy: str,
        timeframe: str,
        stage: DecisionStage,
        direction: str | None = None,
        attempt_no: int = 1,
        source: str = "TRADING_ENGINE",
    ) -> SignalDecisionEvent:
        reason = (
            DecisionReason.PASSED
            if self.allowed
            else self.reason
        )

        return SignalDecisionEvent(
            signal_id=signal_id,
            symbol=symbol,
            strategy=strategy,
            timeframe=timeframe,
            stage=stage,
            outcome=self.outcome,
            reason=reason,
            direction=direction,
            attempt_no=attempt_no,
            source=source,
            context=self.context,
        )
