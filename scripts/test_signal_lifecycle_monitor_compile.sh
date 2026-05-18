#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile \
  src/scripts/monitor_signal_lifecycle.py \
  src/finam_core/runtime/signal_lifecycle_engine.py

echo "OK: signal lifecycle monitor compile"
