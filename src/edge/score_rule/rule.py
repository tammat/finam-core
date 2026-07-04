from __future__ import annotations

import time
from typing import Any

from edge.base.registry import EdgeRuleRegistry
from edge.base.result import EdgeRuleDiagnostics, EdgeRuleResult
from edge.base.rule import EdgeRule
from edge.score_rule.config import EdgeScoreRuleConfig


def _num(value: object, default: float = 0.0) -> float:
    if value is None:
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _clamp01(value: float) -> float:
    return max(0.0, min(1.0, value))


@EdgeRuleRegistry.register
class EdgeScoreRule(EdgeRule):
    name = "EDGE_SCORE_RULE"
    version = "v1"
    enabled = True

    def __init__(self, config: EdgeScoreRuleConfig | None = None) -> None:
        self.config = config or EdgeScoreRuleConfig()

    def run(self, signal_snapshot: dict[str, Any]) -> EdgeRuleResult:
        started = time.perf_counter()
        cfg = self.config

        signal_score = _clamp01(_num(signal_snapshot.get("signal_score")))
        confidence = _clamp01(_num(signal_snapshot.get("confidence")))
        feature_quality_score = _clamp01(_num(signal_snapshot.get("feature_quality_score")))

        weights = {
            "signal_score": cfg.signal_score_weight,
            "confidence": cfg.confidence_weight,
            "feature_quality_score": cfg.feature_quality_weight,
        }

        total_weight = sum(weights.values())
        if total_weight <= 0:
            score = 0.0
            reason = "INVALID_WEIGHTS"
        else:
            score = (
                signal_score * cfg.signal_score_weight
                + confidence * cfg.confidence_weight
                + feature_quality_score * cfg.feature_quality_weight
            ) / total_weight
            reason = "EDGE_SCORE_CALCULATED"

        diagnostics = EdgeRuleDiagnostics(
            input_values={
                "signal_score": signal_score,
                "confidence": confidence,
                "feature_quality_score": feature_quality_score,
            },
            weights=weights,
            component_scores={
                "weighted_signal_score": signal_score * cfg.signal_score_weight,
                "weighted_confidence": confidence * cfg.confidence_weight,
                "weighted_feature_quality": feature_quality_score * cfg.feature_quality_weight,
                "total_score": _clamp01(score),
            },
            execution_time_ms=(time.perf_counter() - started) * 1000.0,
            details={},
        )

        return EdgeRuleResult(
            rule_name=self.name,
            rule_version=self.version,
            score=_clamp01(score),
            diagnostics=diagnostics,
            reason_code=reason,
        )
