#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile \
  src/scripts/build_strategy_rank_decisions_daily.py \
  src/finam_core/analytics/strategy_rank_persistence.py \
  src/finam_core/analytics/strategy_ranker.py

python src/scripts/build_strategy_rank_decisions_daily.py --help >/dev/null

echo "OK: build_strategy_rank_decisions_daily compile"
