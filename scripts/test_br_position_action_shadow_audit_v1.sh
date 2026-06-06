#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python3 -m py_compile \
  src/finam_core/signals/position_action.py \
  src/scripts/analytics/build_br_position_action_shadow_audit_v1.py

python3 src/scripts/analytics/build_br_position_action_shadow_audit_v1.py | \
  tee /tmp/br_position_action_shadow_audit_v1.log

grep -q "BR POSITION ACTION SHADOW AUDIT V1" /tmp/br_position_action_shadow_audit_v1.log
grep -q "ACTION_BY_SIDE" /tmp/br_position_action_shadow_audit_v1.log
grep -q "ACTION_BY_SYMBOL" /tmp/br_position_action_shadow_audit_v1.log
grep -q "SHORT_ACTION_SUMMARY" /tmp/br_position_action_shadow_audit_v1.log
grep -Eq "VERDICT=BR_SHORT_ACTION_EXISTS|VERDICT=BR_SHORT_ACTION_ABSENT" \
  /tmp/br_position_action_shadow_audit_v1.log

echo BR_POSITION_ACTION_SHADOW_AUDIT_V1_OK
