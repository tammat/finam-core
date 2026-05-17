#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile \
  src/scripts/build_strategy_scorecard_daily.py \
  src/finam_core/analytics/strategy_scorecard.py \
  src/finam_core/analytics/strategy_scorecard_persistence.py

python src/scripts/build_strategy_scorecard_daily.py --help >/dev/null

echo "OK: build_strategy_scorecard_daily compile"
