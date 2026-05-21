#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH="${PYTHONPATH:-src}"

python -m py_compile \
  src/finam_core/analytics/exit_optimization.py \
  src/finam_core/analytics/exit_optimization_repository.py \
  scripts/analytics/build_exit_optimization.py

echo "TEST_EXIT_OPTIMIZATION_COMPILE_OK"
