#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile \
  src/finam_core/common/strategy_names.py \
  src/finam_core/analytics/trade_context_snapshot_repository.py \
  src/finam_core/research/research_verdict_repository.py \
  src/finam_core/analytics/strategy_ranking_v2_repository.py \
  src/scripts/build_strategy_promotion_feed.py \
  src/scripts/runtime/build_runtime_strategy_selection.py \
  src/scripts/build_strategy_lifecycle_state.py \
  src/finam_core/runtime/strategy_promotion_engine_repository.py

grep -R -q "normalize_strategy_name" \
  src/finam_core/analytics/trade_context_snapshot_repository.py \
  src/finam_core/research/research_verdict_repository.py \
  src/finam_core/analytics/strategy_ranking_v2_repository.py \
  src/scripts/build_strategy_promotion_feed.py \
  src/scripts/runtime/build_runtime_strategy_selection.py \
  src/scripts/build_strategy_lifecycle_state.py \
  src/finam_core/runtime/strategy_promotion_engine_repository.py

echo "DOWNSTREAM_STRATEGY_CANONICALIZATION_TEST_OK"
