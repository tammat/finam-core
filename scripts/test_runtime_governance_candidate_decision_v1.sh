#!/usr/bin/env bash
set -euo pipefail

ROOT="$(git rev-parse --show-toplevel)"
cd "$ROOT"

export PYTHONPATH=src

python3 -m py_compile \
    src/scripts/analytics/build_runtime_governance_candidate_decision_v1.py

python3 \
    src/scripts/analytics/build_runtime_governance_candidate_decision_v1.py \
    | tee /tmp/runtime_governance_candidate_decision_v1.log

grep -q "decision=WATCH_ONLY" \
    /tmp/runtime_governance_candidate_decision_v1.log

grep -q "runtime_allow=0" \
    /tmp/runtime_governance_candidate_decision_v1.log

grep -q "shadow_allow=1" \
    /tmp/runtime_governance_candidate_decision_v1.log

grep -q "watch_allow=1" \
    /tmp/runtime_governance_candidate_decision_v1.log

grep -q "VERDICT=RUNTIME_GOVERNANCE_REJECT_RUNTIME_ALLOW" \
    /tmp/runtime_governance_candidate_decision_v1.log

grep -q "RUNTIME_GOVERNANCE_CANDIDATE_DECISION_V1_OK" \
    /tmp/runtime_governance_candidate_decision_v1.log

echo TEST_RUNTIME_GOVERNANCE_CANDIDATE_DECISION_V1_OK
