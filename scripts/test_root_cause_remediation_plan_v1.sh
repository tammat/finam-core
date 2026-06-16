#!/usr/bin/env bash
set -euo pipefail

cd "$(git rev-parse --show-toplevel)"
export PYTHONPATH=src

python3 -m py_compile \
  src/scripts/research/build_root_cause_remediation_plan_v1.py

python3 \
  src/scripts/research/build_root_cause_remediation_plan_v1.py \
  | tee /tmp/root_cause_remediation_plan_v1.log

grep -q "ROOT CAUSE REMEDIATION PLAN V1" \
  /tmp/root_cause_remediation_plan_v1.log

grep -q "ROOT_CAUSE_REMEDIATION_SUMMARY" \
  /tmp/root_cause_remediation_plan_v1.log

grep -q "ROOT_CAUSE_REMEDIATION_PLAN_V1_OK" \
  /tmp/root_cause_remediation_plan_v1.log

echo TEST_ROOT_CAUSE_REMEDIATION_PLAN_V1_OK
