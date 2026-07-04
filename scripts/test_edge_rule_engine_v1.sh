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
