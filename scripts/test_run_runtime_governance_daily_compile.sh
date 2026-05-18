#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile \
  src/scripts/run_runtime_governance_daily.py \
  src/finam_core/runtime/runtime_governance_coordinator.py \
  src/finam_core/analytics/strategy_scorecard_persistence.py \
  src/finam_core/analytics/strategy_rank_persistence.py \
  src/finam_core/runtime/runtime_strategy_cooldown_builder.py \
  src/finam_core/runtime/runtime_universe_allocator.py

python src/scripts/run_runtime_governance_daily.py --help >/dev/null

echo "OK: run_runtime_governance_daily compile"
