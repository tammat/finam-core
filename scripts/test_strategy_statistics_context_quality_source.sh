#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile \
  src/finam_core/analytics/strategy_statistics_v2_repository.py \
  src/scripts/build_strategy_statistics_v2.py

grep -q "trade_context_snapshots" src/finam_core/analytics/strategy_statistics_v2_repository.py
grep -q "COALESCE(tcs.context_quality, a.attribution_quality)" src/finam_core/analytics/strategy_statistics_v2_repository.py

echo "STRATEGY_STATISTICS_CONTEXT_QUALITY_SOURCE_OK"
