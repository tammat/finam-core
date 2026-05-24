#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile src/scripts/analytics/build_strategy_regime_matrix.py

python - <<'PY'
from scripts.analytics.build_strategy_regime_matrix import classify_matrix_action

assert classify_matrix_action(
    context_status="STRONG_CONTEXT",
    trades=30,
    profit_factor=1.4,
    expectancy=0.2,
)[0] == "ALLOW"

assert classify_matrix_action(
    context_status="WATCH_CONTEXT",
    trades=82,
    profit_factor=1.15,
    expectancy=0.47,
)[0] == "WATCH"

assert classify_matrix_action(
    context_status="BAD_CONTEXT",
    trades=13,
    profit_factor=0.76,
    expectancy=-0.41,
)[0] == "BLOCK"

assert classify_matrix_action(
    context_status="LOW_SAMPLE",
    trades=3,
    profit_factor=2.0,
    expectancy=1.0,
)[0] == "WATCH"

print("STRATEGY_REGIME_MATRIX_V1_UNIT_OK")
PY

grep -q "strategy_regime_matrix" scripts/migrate_strategy_regime_matrix_v1.sh
grep -q "STRATEGY_REGIME_MATRIX_V1_OK" src/scripts/analytics/build_strategy_regime_matrix.py

echo "STRATEGY_REGIME_MATRIX_V1_TEST_OK"
