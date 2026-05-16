from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from finam_core.strategy.signal_confidence import (
    SignalConfidenceDecision,
    SignalConfidenceEngine,
)


@dataclass(frozen=True)
class EntryConfidenceGateDecision:
    accepted: bool
    confidence: float
    institutional_confirmed: bool
    action: str
    reason: str


class EntryConfidenceGate:
    """Русский комментарий: confirmation gate перед RiskEngine."""

    def __init__(
        self,
        engine: SignalConfidenceEngine | None = None,
        min_confidence: float = 0.55,
    ) -> None:
        self.engine = engine or SignalConfidenceEngine()
        self.min_confidence = float(min_confidence)

    def evaluate(
        self,
        intent: dict[str, Any],
        market_state: dict[str, Any] | None = None,
    ) -> EntryConfidenceGateDecision:
        market_state = market_state or {}

        features = dict(intent.get("features") or {})

        decision: SignalConfidenceDecision = self.engine.evaluate(
            base_score=float(features.get("base_score", 0.5)),
            smart_money_score=float(features.get("smart_money_score", 0.0)),
            regime_alignment=float(features.get("regime_alignment", 0.5)),
            spread_quality=float(features.get("spread_quality", 1.0)),
            volatility_quality=float(features.get("volatility_quality", 0.5)),
        )

        accepted = (
            decision.action != "REJECT"
            and decision.confidence >= self.min_confidence
        )

        reason = (
            f"{decision.reason};"
            f"min_confidence={self.min_confidence};"
            f"accepted={accepted}"
        )

        return EntryConfidenceGateDecision(
            accepted=accepted,
            confidence=decision.confidence,
            institutional_confirmed=decision.institutional_confirmed,
            action=decision.action,
            reason=reason,
        )
