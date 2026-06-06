#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python3 -m py_compile \
  src/scripts/analytics/build_br_short_policy_decision_v1.py

python3 src/scripts/analytics/build_br_short_policy_decision_v1.py | \
  tee /tmp/br_short_policy_decision_v1.log

grep -q "BR SHORT POLICY DECISION V1" /tmp/br_short_policy_decision_v1.log
grep -q "STRATEGY_DECISIONS" /tmp/br_short_policy_decision_v1.log
grep -q "POLICY_DECISION" /tmp/br_short_policy_decision_v1.log
grep -Eq "VERDICT=ALLOW_BR_CANONICAL_SHORT_IN_SHADOW_ONLY|VERDICT=DO_NOT_ENABLE_BR_SHORT" \
  /tmp/br_short_policy_decision_v1.log

echo BR_SHORT_POLICY_DECISION_V1_OK
