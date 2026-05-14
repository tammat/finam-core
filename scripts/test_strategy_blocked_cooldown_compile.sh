#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile \
  src/finam_core/control/adaptive_strategy_controller.py \
  src/scripts/run_strategy_performance_monitor.py

echo "OK: strategy blocked cooldown compiles"
