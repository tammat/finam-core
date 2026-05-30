#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core
export PYTHONPATH=src

echo "TEST_USD_GOVERNANCE_SENSITIVITY_V1_START"

python -m py_compile \
src/scripts/analytics/build_usd_governance_sensitivity_v1.py

python src/scripts/analytics/build_usd_governance_sensitivity_v1.py \
> /tmp/usd_governance_sensitivity_v1.out

grep -q "USD_GOVERNANCE_SENSITIVITY" /tmp/usd_governance_sensitivity_v1.out
grep -q "USD_SENSITIVITY_CANDIDATE" /tmp/usd_governance_sensitivity_v1.out
grep -q "USD_SENSITIVITY_ROW" /tmp/usd_governance_sensitivity_v1.out

echo "TEST_USD_GOVERNANCE_SENSITIVITY_V1_OK"
