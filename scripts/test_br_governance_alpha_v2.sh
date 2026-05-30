#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core
export PYTHONPATH=src

echo "TEST_BR_GOVERNANCE_ALPHA_V2_START"

python -m py_compile src/scripts/analytics/build_br_governance_alpha_v2.py

python src/scripts/analytics/build_br_governance_alpha_v2.py \
  --window-days 30 \
  --min-closed-trades 5 \
  --min-governance-rows 5 | tee /tmp/br_governance_alpha_v2.out

grep -q "BR_GOVERNANCE_ALPHA_V2" /tmp/br_governance_alpha_v2.out
grep -q "BR_POLICY_CANDIDATE" /tmp/br_governance_alpha_v2.out
grep -q "BR_POLICY_SUMMARY" /tmp/br_governance_alpha_v2.out
grep -q "BR_GOVERNANCE_ALPHA_V2_OK" /tmp/br_governance_alpha_v2.out

echo "TEST_BR_GOVERNANCE_ALPHA_V2_OK"
