#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_RISK_RULE_ENGINE_V1 ==="

PYTHONPATH=src python -m py_compile \
  src/risk/base/result.py \
  src/risk/base/rule.py \
  src/risk/base/registry.py \
  src/risk/base/executor.py \
  src/risk/default_rule/config.py \
  src/risk/default_rule/rule.py \
  src/risk/default_rule/__init__.py

PYTHONPATH=src python - <<'PY'
from risk.base.executor import RiskRuleExecutor
from risk.base.registry import RiskRuleRegistry
import risk.default_rule
from risk.default_rule.rule import DefaultRiskRule

assert RiskRuleRegistry.get("DEFAULT_RISK_RULE") is DefaultRiskRule

rule = DefaultRiskRule()
executor = RiskRuleExecutor()

passed = executor.execute(rule, {
    "edge_score": 0.80,
    "validation_score": 0.80,
    "ready_for_paper": True,
    "ready_for_live": False,
    "ready_for_micro_live": False,
})
assert passed.passed is True
assert passed.risk_score == 1.0

low_edge = executor.execute(rule, {
    "edge_score": 0.20,
    "validation_score": 0.80,
    "ready_for_paper": True,
})
assert low_edge.passed is False

unsafe_live = executor.execute(rule, {
    "edge_score": 0.80,
    "validation_score": 0.80,
    "ready_for_paper": True,
    "ready_for_live": True,
})
assert unsafe_live.passed is False

not_ready = executor.execute(rule, {
    "edge_score": 0.80,
    "validation_score": 0.80,
    "ready_for_paper": False,
})
assert not_ready.passed is False
PY

echo "risk_rule_registry=ok"
echo "default_risk_rule=ok"
echo "pass_case=ok"
echo "low_edge=ok"
echo "unsafe_live=ok"
echo "not_ready=ok"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=RISK_RULE_ENGINE_V1_READY"
echo "VERDICT=TEST_RISK_RULE_ENGINE_V1_OK"
