#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile \
  src/finam_core/runtime/regime_matrix_modifier.py \
  src/scripts/runtime/apply_regime_matrix_runtime_modifier.py

python - <<'PY'
from finam_core.runtime.regime_matrix_modifier import build_regime_matrix_runtime_decision

allow = build_regime_matrix_runtime_decision(
    runtime_action="ALLOW",
    score_adjustment=0.15,
    confidence_adjustment=0.10,
)
assert allow.suffix == "REGIME_ALLOW"
assert allow.score_delta > 0

watch = build_regime_matrix_runtime_decision(
    runtime_action="WATCH",
    score_adjustment=0.06,
    confidence_adjustment=0.04,
)
assert watch.suffix == "REGIME_WATCH"
assert watch.score_delta == 0.06

block = build_regime_matrix_runtime_decision(
    runtime_action="BLOCK",
    score_adjustment=-0.30,
    confidence_adjustment=-0.20,
)
assert block.suffix == "REGIME_BLOCK"
assert block.score_delta < 0

print("REGIME_MATRIX_RUNTIME_MODIFIER_UNIT_OK")
PY

grep -q "strategy_regime_matrix" src/scripts/runtime/apply_regime_matrix_runtime_modifier.py
grep -q "REGIME_MATRIX_RUNTIME_MODIFIER_OK" src/scripts/runtime/apply_regime_matrix_runtime_modifier.py

echo "REGIME_MATRIX_RUNTIME_MODIFIER_V2_TEST_OK"
