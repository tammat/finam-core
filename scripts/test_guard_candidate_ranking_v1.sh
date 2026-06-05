#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python3 -m py_compile src/scripts/analytics/build_guard_candidate_ranking_v1.py

python3 src/scripts/analytics/build_guard_candidate_ranking_v1.py | tee /tmp/guard_candidate_ranking_v1.log

grep -q "VERDICT=OK" /tmp/guard_candidate_ranking_v1.log
grep -q "WORST_BY_NET_PNL" /tmp/guard_candidate_ranking_v1.log
grep -q "BEST_BY_EXPECTANCY_MIN3" /tmp/guard_candidate_ranking_v1.log

echo GUARD_CANDIDATE_RANKING_V1_OK
