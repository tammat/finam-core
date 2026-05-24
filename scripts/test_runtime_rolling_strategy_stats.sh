#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH="${PYTHONPATH:-src}"

python -m py_compile src/scripts/build_runtime_rolling_strategy_stats.py

grep -q "runtime_rolling_strategy_stats" src/scripts/build_runtime_rolling_strategy_stats.py
grep -q "RUNTIME_ROLLING_STRATEGY_STATS" src/scripts/build_runtime_rolling_strategy_stats.py

echo "TEST_RUNTIME_ROLLING_STRATEGY_STATS_OK"
