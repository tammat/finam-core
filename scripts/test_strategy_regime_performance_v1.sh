#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile src/scripts/analytics/build_strategy_regime_performance.py

python - <<'PY'
from scripts.analytics.build_strategy_regime_performance import classify_status

assert classify_status(trades=5, profit_factor=2.0, expectancy=1.0, winrate=0.8)[0] == "LOW_SAMPLE"
assert classify_status(trades=20, profit_factor=1.4, expectancy=0.1, winrate=0.5)[0] == "STRONG_CONTEXT"
assert classify_status(trades=20, profit_factor=1.1, expectancy=0.1, winrate=0.4)[0] == "WATCH_CONTEXT"
assert classify_status(trades=20, profit_factor=0.7, expectancy=-0.1, winrate=0.3)[0] == "BAD_CONTEXT"

print("STRATEGY_REGIME_PERFORMANCE_V1_UNIT_OK")
PY

grep -q "strategy_regime_performance" scripts/migrate_strategy_regime_performance_v1.sh
grep -q "STRATEGY_REGIME_PERFORMANCE_V1_OK" src/scripts/analytics/build_strategy_regime_performance.py

echo "STRATEGY_REGIME_PERFORMANCE_V1_TEST_OK"
