#!/usr/bin/env bash
set -euo pipefail

python -m py_compile src/finam_core/analytics/strategy_ranking_v2_repository.py

grep -q 'research_verdict == "CANDIDATE"' src/finam_core/analytics/strategy_ranking_v2_repository.py
grep -q 'research_verdict == "BLOCK"' src/finam_core/analytics/strategy_ranking_v2_repository.py
grep -q 'research_verdict == "RESEARCH_ONLY"' src/finam_core/analytics/strategy_ranking_v2_repository.py
grep -q "strategy_research_verdicts" src/finam_core/analytics/strategy_ranking_v2_repository.py

echo "STRATEGY_RANKING_RESEARCH_VERDICT_WIRING_TEST_OK"
