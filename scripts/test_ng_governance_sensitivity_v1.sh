#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core
export PYTHONPATH=src

echo "TEST_NG_GOVERNANCE_SENSITIVITY_V1_START"

python -m py_compile src/scripts/analytics/build_ng_governance_sensitivity_v1.py

python src/scripts/analytics/build_ng_governance_sensitivity_v1.py \
  > /tmp/ng_governance_sensitivity_v1.out

grep -q "NG_GOVERNANCE_SENSITIVITY_V1" /tmp/ng_governance_sensitivity_v1.out
grep -q "NG_SENSITIVITY_CONFIG" /tmp/ng_governance_sensitivity_v1.out
grep -q "NG_SENSITIVITY_ROW" /tmp/ng_governance_sensitivity_v1.out
grep -q "NG_GOVERNANCE_SENSITIVITY_V1_OK" /tmp/ng_governance_sensitivity_v1.out

echo "TEST_NG_GOVERNANCE_SENSITIVITY_V1_OK"
