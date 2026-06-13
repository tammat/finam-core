#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python3 -m py_compile src/scripts/analytics/build_br_short_policy_reachability_audit_v1.py

python3 src/scripts/analytics/build_br_short_policy_reachability_audit_v1.py | \
  tee /tmp/br_short_policy_reachability_audit_v1.log

grep -q "BR SHORT POLICY REACHABILITY AUDIT V1" /tmp/br_short_policy_reachability_audit_v1.log
grep -q "METRIC_ROW name=sell_candidate" /tmp/br_short_policy_reachability_audit_v1.log
grep -q "METRIC_ROW name=short_policy" /tmp/br_short_policy_reachability_audit_v1.log
grep -q "VERDICT=" /tmp/br_short_policy_reachability_audit_v1.log
grep -q "BR_SHORT_POLICY_REACHABILITY_AUDIT_V1_OK" /tmp/br_short_policy_reachability_audit_v1.log

echo TEST_BR_SHORT_POLICY_REACHABILITY_AUDIT_V1_OK
