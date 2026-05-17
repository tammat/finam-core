#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile \
  src/scripts/run_runtime_execution_engine.py \
  src/finam_core/runtime/runtime_execution_engine.py \
  src/finam_core/runtime/runtime_rebalance_cycle.py \
  src/finam_core/runtime/runtime_telemetry.py \
  src/finam_core/data/runtime_universe_provider.py \
  src/finam_core/runtime/runtime_universe_allocator.py

echo "OK: run_runtime_execution_engine compile"
