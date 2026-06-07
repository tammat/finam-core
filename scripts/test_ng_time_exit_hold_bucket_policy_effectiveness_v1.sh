#!/usr/bin/env bash
set -euo pipefail

ROOT="$(git rev-parse --show-toplevel)"
cd "$ROOT"
export PYTHONPATH=src

python3 -m py_compile \
  src/finam_core/governance/ng_time_exit_hold_bucket_policy_v1.py \
  src/scripts/analytics/build_ng_time_exit_hold_bucket_policy_effectiveness_v1.py

python3 src/scripts/analytics/build_ng_time_exit_hold_bucket_policy_effectiveness_v1.py | \
  tee /tmp/ng_time_exit_hold_bucket_policy_effectiveness_v1.log

grep -q "NG TIME EXIT HOLD BUCKET POLICY EFFECTIVENESS V1" /tmp/ng_time_exit_hold_bucket_policy_effectiveness_v1.log
grep -q "POLICY_ACTION_SUMMARY" /tmp/ng_time_exit_hold_bucket_policy_effectiveness_v1.log
grep -q "EFFECTIVENESS" /tmp/ng_time_exit_hold_bucket_policy_effectiveness_v1.log
grep -q "DELTA_ROW" /tmp/ng_time_exit_hold_bucket_policy_effectiveness_v1.log
grep -q "NG_TIME_EXIT_HOLD_BUCKET_POLICY_EFFECTIVENESS_V1_OK" /tmp/ng_time_exit_hold_bucket_policy_effectiveness_v1.log

echo TEST_NG_TIME_EXIT_HOLD_BUCKET_POLICY_EFFECTIVENESS_V1_OK
