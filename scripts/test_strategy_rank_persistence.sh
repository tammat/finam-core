#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile \
  src/finam_core/analytics/strategy_ranker.py \
  src/finam_core/analytics/strategy_rank_persistence.py

echo "OK: strategy rank persistence compile"
