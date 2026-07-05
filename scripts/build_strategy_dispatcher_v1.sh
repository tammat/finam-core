#!/usr/bin/env bash
set -euo pipefail

echo "=== BUILD_STRATEGY_DISPATCHER_V1 ==="

sudo -u postgres psql -v ON_ERROR_STOP=1 -d finam_core \
  -f sql/analytics/019_strategy_dispatcher_v1.sql

PYTHONPATH=src python -m py_compile \
  src/marketcore/research/execution/dispatchers/strategy_dispatcher.py \
  src/marketcore/presentation/ui_labels.py

scripts/test_strategy_dispatcher_v1.sh

echo "VERDICT=BUILD_STRATEGY_DISPATCHER_V1_OK"
