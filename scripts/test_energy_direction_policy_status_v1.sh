#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python3 -m py_compile src/scripts/analytics/build_energy_direction_policy_status_v1.py

python3 src/scripts/analytics/build_energy_direction_policy_status_v1.py | \
  tee /tmp/energy_direction_policy_status_v1.log

grep -q "ENERGY DIRECTION POLICY STATUS V1" /tmp/energy_direction_policy_status_v1.log
grep -q "POLICY_ROW root=BR" /tmp/energy_direction_policy_status_v1.log
grep -q "POLICY_ROW root=NG" /tmp/energy_direction_policy_status_v1.log
grep -q "BR_LONG=SHADOW_OR_BLOCKED" /tmp/energy_direction_policy_status_v1.log
grep -q "NG_SHORT=BLOCKED" /tmp/energy_direction_policy_status_v1.log
grep -q "ENERGY_DIRECTION_POLICY_STATUS_V1_OK" /tmp/energy_direction_policy_status_v1.log

echo TEST_ENERGY_DIRECTION_POLICY_STATUS_V1_OK
