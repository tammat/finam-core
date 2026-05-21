#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH="${PYTHONPATH:-src}"

python -m py_compile \
  src/finam_core/analytics/statistics_repository.py \
  scripts/analytics/build_trade_statistics.py

echo "TEST_STATISTICS_REPOSITORY_COMPILE_OK"
