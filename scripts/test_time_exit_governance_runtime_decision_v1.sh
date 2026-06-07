#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core
export PYTHONPATH=src

python3 -m py_compile \
  src/scripts/analytics/build_time_exit_governance_runtime_decision_v1.py

python3 src/scripts/analytics/build_time_exit_governance_runtime_decision_v1.py | \
  tee /tmp/time_exit_governance_runtime_decision_v1.log

grep -q "TIME EXIT GOVERNANCE RUNTIME DECISION V1" /tmp/time_exit_governance_runtime_decision_v1.log
grep -q "INPUT_METRICS" /tmp/time_exit_governance_runtime_decision_v1.log
grep -q "RUNTIME_DECISION" /tmp/time_exit_governance_runtime_decision_v1.log
grep -q "POLICY_MATRIX" /tmp/time_exit_governance_runtime_decision_v1.log
grep -q "TIME_EXIT_GOVERNANCE_RUNTIME_DECISION_V1_OK" /tmp/time_exit_governance_runtime_decision_v1.log

echo TEST_TIME_EXIT_GOVERNANCE_RUNTIME_DECISION_V1_OK
