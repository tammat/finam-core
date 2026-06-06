#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python3 -m py_compile src/scripts/analytics/build_br_exit_policy_candidate_v1.py

python3 src/scripts/analytics/build_br_exit_policy_candidate_v1.py | \
  tee /tmp/br_exit_policy_candidate_v1.log

grep -q "BR EXIT POLICY CANDIDATE V1" /tmp/br_exit_policy_candidate_v1.log
grep -q "CANDIDATE_POLICIES" /tmp/br_exit_policy_candidate_v1.log
grep -q "RANKING" /tmp/br_exit_policy_candidate_v1.log
grep -q "WINNER_POLICY=" /tmp/br_exit_policy_candidate_v1.log
grep -Eq "VERDICT=EXIT_POLICY_CANDIDATE_FOUND|VERDICT=NO_POLICY_PASSED|VERDICT=NO_DATA" \
  /tmp/br_exit_policy_candidate_v1.log

echo BR_EXIT_POLICY_CANDIDATE_V1_OK
