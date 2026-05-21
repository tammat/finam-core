#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH="${PYTHONPATH:-src}"

python -m py_compile \
  src/finam_core/analytics/symbol_strategy_mapper.py \
  src/scripts/analytics_runtime_supervisor.py

echo "TEST_ANALYTICS_RUNTIME_SUPERVISOR_COMPILE_OK"
