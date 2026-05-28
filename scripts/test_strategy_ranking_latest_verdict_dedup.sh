#!/usr/bin/env bash
set -euo pipefail

python -m py_compile src/finam_core/analytics/strategy_ranking_v2_repository.py

grep -q "SELECT DISTINCT ON (symbol, strategy, timeframe, trade_source)" src/finam_core/analytics/strategy_ranking_v2_repository.py
grep -q "WHEN regime <> 'unknown'" src/finam_core/analytics/strategy_ranking_v2_repository.py
grep -q "WHEN 'CANDIDATE' THEN 0" src/finam_core/analytics/strategy_ranking_v2_repository.py

echo "STRATEGY_RANKING_LATEST_VERDICT_DEDUP_TEST_OK"
