#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile \
  src/scripts/rank_strategies_daily.py \
  src/finam_core/analytics/strategy_ranker.py

python src/scripts/rank_strategies_daily.py --help >/dev/null

echo "OK: rank_strategies_daily compile"
