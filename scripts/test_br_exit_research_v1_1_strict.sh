#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python3 -m py_compile src/scripts/analytics/build_br_exit_research_v1_1_strict.py

python3 src/scripts/analytics/build_br_exit_research_v1_1_strict.py | \
  tee /tmp/br_exit_research_v1_1_strict.log

grep -q "BR EXIT RESEARCH V1.1 STRICT" /tmp/br_exit_research_v1_1_strict.log
grep -q "lookahead=disabled" /tmp/br_exit_research_v1_1_strict.log
grep -q "POLICIES" /tmp/br_exit_research_v1_1_strict.log
grep -q "RANKING" /tmp/br_exit_research_v1_1_strict.log
grep -q "WINNER_POLICY=" /tmp/br_exit_research_v1_1_strict.log
grep -Eq "VERDICT=STRICT_EXIT_CANDIDATE_FOUND|VERDICT=NO_STRICT_POLICY_PASSED|VERDICT=NO_DATA" \
  /tmp/br_exit_research_v1_1_strict.log

echo BR_EXIT_RESEARCH_V1_1_STRICT_OK
