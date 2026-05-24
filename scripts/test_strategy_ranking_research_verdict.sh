#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile \
  src/finam_core/analytics/strategy_ranking_v2_repository.py \
  src/scripts/build_strategy_ranking_v2.py

grep -q "strategy_research_verdicts" src/finam_core/analytics/strategy_ranking_v2_repository.py
grep -q "WATCH_DIVERGENCE" src/finam_core/analytics/strategy_ranking_v2_repository.py
grep -q "research_verdict:" src/finam_core/analytics/strategy_ranking_v2_repository.py

echo "STRATEGY_RANKING_RESEARCH_VERDICT_TEST_OK"
