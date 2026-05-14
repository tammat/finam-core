#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile src/scripts/run_strategy_performance_monitor.py

echo "OK: strategy performance monitor compiles"
