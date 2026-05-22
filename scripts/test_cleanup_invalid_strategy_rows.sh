#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH="${PYTHONPATH:-src}"

python -m py_compile \
  src/scripts/cleanup_invalid_strategy_rows.py \
  src/finam_core/analytics/strategy_ranking_v2_repository.py

grep -q "strategy_promotion_decisions" src/scripts/cleanup_invalid_strategy_rows.py
grep -q "COALESCE(strategy" src/scripts/cleanup_invalid_strategy_rows.py

echo "TEST_CLEANUP_INVALID_STRATEGY_ROWS_OK"
