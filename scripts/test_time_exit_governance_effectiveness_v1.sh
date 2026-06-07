#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core
export PYTHONPATH=src

test -f src/scripts/analytics/build_time_exit_governance_effectiveness_v1.py

python3 -m py_compile \
  src/finam_core/governance/time_exit_governance_v1.py \
  src/scripts/analytics/build_time_exit_governance_effectiveness_v1.py

python3 src/scripts/analytics/build_time_exit_governance_effectiveness_v1.py | \
  tee /tmp/time_exit_governance_effectiveness_v1.log

grep -q "TIME EXIT GOVERNANCE EFFECTIVENESS V1" /tmp/time_exit_governance_effectiveness_v1.log
grep -q "GOVERNANCE_ACTION_SUMMARY" /tmp/time_exit_governance_effectiveness_v1.log
grep -q "ROOT_EFFECTIVENESS" /tmp/time_exit_governance_effectiveness_v1.log
grep -q "TIME_EXIT_GOVERNANCE_EFFECTIVENESS_V1_OK" /tmp/time_exit_governance_effectiveness_v1.log

echo TEST_TIME_EXIT_GOVERNANCE_EFFECTIVENESS_V1_OK
