#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH="${PYTHONPATH:-src}"

python -m py_compile \
  src/finam_core/analytics/drawdown_summary.py \
  src/finam_core/analytics/statistics_repository.py \
  scripts/analytics/build_drawdown_summary.py

echo "TEST_BUILD_DRAWDOWN_SUMMARY_COMPILE_OK"
