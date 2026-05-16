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

        institutional_flow_regime = str(
            features.get("institutional_flow_regime") or "UNKNOWN"
        )
        institutional_flow_bias = str(
            features.get("institutional_flow_bias") or "NEUTRAL"
        )

        confidence = decision.confidence
        flow_adjustment = 0.0

        if institutional_flow_regime == "ACCUMULATION":
            flow_adjustment = 0.08
        elif institutional_flow_regime == "TREND_INITIATION":
            flow_adjustment = 0.10
        elif institutional_flow_regime == "INSTITUTIONAL_PARTICIPATION":
            flow_adjustment = 0.06
        elif institutional_flow_regime == "BREAKOUT_TRAP":
            flow_adjustment = -0.20

        confidence = round(max(0.0, min(confidence + flow_adjustment, 1.0)), 6)

        accepted = (
            decision.action != "REJECT"
            and confidence >= self.min_confidence
        )

        reason = (
            f"{decision.reason};"
            f"institutional_flow_regime={institutional_flow_regime};"
            f"institutional_flow_bias={institutional_flow_bias};"
            f"flow_adjustment={flow_adjustment};"
            f"min_confidence={self.min_confidence};"
            f"accepted={accepted}"
        )

        return EntryConfidenceGateDecision(
            accepted=accepted,
            confidence=confidence,
            institutional_confirmed=decision.institutional_confirmed,
            action=decision.action,
            reason=reason,
        )
