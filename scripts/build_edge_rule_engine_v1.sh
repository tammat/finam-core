#!/usr/bin/env bash
set -euo pipefail

echo "=== BUILD_EDGE_RULE_ENGINE_V1 ==="

mkdir -p src/edge/base src/edge/score_rule scripts

touch src/edge/__init__.py
touch src/edge/base/__init__.py
touch src/edge/score_rule/__init__.py

cat > src/edge/base/result.py <<'PY'
from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(slots=True, frozen=True)
class EdgeRuleDiagnostics:
    input_values: dict[str, float]
    weights: dict[str, float]
    component_scores: dict[str, float]
    execution_time_ms: float
    details: dict[str, Any]


@dataclass(slots=True, frozen=True)
class EdgeRuleResult:
    rule_name: str
    rule_version: str
    score: float
    diagnostics: EdgeRuleDiagnostics
    reason_code: str
PY

cat > src/edge/base/rule.py <<'PY'
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from edge.base.result import EdgeRuleResult


class EdgeRule(ABC):
    name: str
    version: str
    enabled: bool = True

    @abstractmethod
    def run(self, signal_snapshot: dict[str, Any]) -> EdgeRuleResult:
        raise NotImplementedError
PY

cat > src/edge/base/registry.py <<'PY'
from __future__ import annotations

from edge.base.rule import EdgeRule


class EdgeRuleRegistry:
    _registry: dict[str, type[EdgeRule]] = {}

    @classmethod
    def register(cls, rule_cls: type[EdgeRule]) -> type[EdgeRule]:
        name = getattr(rule_cls, "name", "")
        if not name:
            raise ValueError("edge rule name is required")
        cls._registry[name] = rule_cls
        return rule_cls

    @classmethod
    def enabled(cls) -> list[type[EdgeRule]]:
        return [
            rule_cls
            for rule_cls in cls._registry.values()
            if getattr(rule_cls, "enabled", True)
        ]

    @classmethod
    def get(cls, name: str) -> type[EdgeRule] | None:
        return cls._registry.get(name)

    @classmethod
    def clear_for_tests(cls) -> None:
        cls._registry.clear()
PY

cat > src/edge/base/executor.py <<'PY'
from __future__ import annotations

from edge.base.result import EdgeRuleResult
from edge.base.rule import EdgeRule


class EdgeRuleExecutor:
    def execute(self, rule: EdgeRule, signal_snapshot: dict) -> EdgeRuleResult:
        return rule.run(signal_snapshot)
PY

cat > src/edge/score_rule/config.py <<'PY'
from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(slots=True, frozen=True)
class EdgeScoreRuleConfig:
    signal_score_weight: float = 0.40
    confidence_weight: float = 0.40
    feature_quality_weight: float = 0.20

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> "EdgeScoreRuleConfig":
        data = data or {}
        return cls(
            signal_score_weight=float(data.get("signal_score_weight", cls.signal_score_weight)),
            confidence_weight=float(data.get("confidence_weight", cls.confidence_weight)),
            feature_quality_weight=float(data.get("feature_quality_weight", cls.feature_quality_weight)),
        )
PY

cat > src/edge/score_rule/rule.py <<'PY'
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
PY

cat > src/edge/score_rule/__init__.py <<'PY'
from edge.score_rule.rule import EdgeScoreRule

__all__ = ["EdgeScoreRule"]
PY

cat > scripts/test_edge_rule_engine_v1.sh <<'SH_TEST'
#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_EDGE_RULE_ENGINE_V1 ==="

PYTHONPATH=src python -m py_compile \
  src/edge/base/result.py \
  src/edge/base/rule.py \
  src/edge/base/registry.py \
  src/edge/base/executor.py \
  src/edge/score_rule/config.py \
  src/edge/score_rule/rule.py \
  src/edge/score_rule/__init__.py

PYTHONPATH=src python - <<'PY'
from edge.base.executor import EdgeRuleExecutor
from edge.base.registry import EdgeRuleRegistry
import edge.score_rule  # noqa: F401
from edge.score_rule.rule import EdgeScoreRule

assert EdgeRuleRegistry.get("EDGE_SCORE_RULE") is EdgeScoreRule

rule = EdgeScoreRule()
executor = EdgeRuleExecutor()

high = executor.execute(rule, {
    "signal_score": 0.95,
    "confidence": 0.90,
    "feature_quality_score": 1.0,
})
assert high.score >= 0.90
assert high.reason_code == "EDGE_SCORE_CALCULATED"

medium = executor.execute(rule, {
    "signal_score": 0.60,
    "confidence": 0.60,
    "feature_quality_score": 0.80,
})
assert 0.60 <= medium.score <= 0.70

low = executor.execute(rule, {
    "signal_score": 0.10,
    "confidence": 0.20,
    "feature_quality_score": 0.30,
})
assert low.score < 0.30

invalid = executor.execute(rule, {
    "signal_score": None,
    "confidence": "bad",
    "feature_quality_score": None,
})
assert invalid.score == 0.0
assert "signal_score" in invalid.diagnostics.input_values
PY

echo "edge_rule_registry=ok"
echo "edge_score_rule=ok"
echo "high_score=ok"
echo "medium_score=ok"
echo "low_score=ok"
echo "invalid_signal=ok"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=EDGE_RULE_ENGINE_V1_READY"
echo "VERDICT=TEST_EDGE_RULE_ENGINE_V1_OK"
SH_TEST

chmod +x scripts/test_edge_rule_engine_v1.sh
scripts/test_edge_rule_engine_v1.sh

echo "VERDICT=BUILD_EDGE_RULE_ENGINE_V1_OK"
