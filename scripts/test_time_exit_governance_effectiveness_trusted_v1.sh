#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core
export PYTHONPATH=src

python3 -m py_compile \
src/scripts/analytics/build_time_exit_governance_effectiveness_trusted_v1.py

python3 \
src/scripts/analytics/build_time_exit_governance_effectiveness_trusted_v1.py \
| tee /tmp/time_exit_governance_effectiveness_trusted_v1.log

grep -q "TRUSTED_EFFECTIVENESS" \
/tmp/time_exit_governance_effectiveness_trusted_v1.log

grep -q "TIME_EXIT_GOVERNANCE_EFFECTIVENESS_TRUSTED_V1_OK" \
/tmp/time_exit_governance_effectiveness_trusted_v1.log

echo TEST_TIME_EXIT_GOVERNANCE_EFFECTIVENESS_TRUSTED_V1_OK
