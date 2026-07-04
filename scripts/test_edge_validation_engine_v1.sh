#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_EDGE_VALIDATION_ENGINE_V1 ==="

PYTHONPATH=src python -m py_compile \
  src/edge/base/validation_result.py \
  src/edge/base/validation_rule.py \
  src/edge/base/validation_registry.py \
  src/edge/base/validation_executor.py \
  src/edge/sample_rule/config.py \
  src/edge/sample_rule/rule.py \
  src/edge/sample_rule/__init__.py

PYTHONPATH=src python - <<'PY'
from edge.base.validation_executor import EdgeValidationExecutor
from edge.base.validation_registry import EdgeValidationRegistry
import edge.sample_rule
from edge.sample_rule.rule import EdgeSampleRule

assert EdgeValidationRegistry.get("EDGE_SAMPLE_RULE") is EdgeSampleRule

rule = EdgeSampleRule()
executor = EdgeValidationExecutor()

assert executor.execute(rule, {"edge_score": 0.80, "samples": 50}).passed is True
assert executor.execute(rule, {"edge_score": 0.30, "samples": 50}).passed is False
assert executor.execute(rule, {"edge_score": 0.80, "samples": 2}).passed is False
assert executor.execute(rule, {"edge_score": None, "samples": None}).passed is False
PY

echo "VERDICT=EDGE_VALIDATION_ENGINE_V1_READY"
echo "VERDICT=TEST_EDGE_VALIDATION_ENGINE_V1_OK"
