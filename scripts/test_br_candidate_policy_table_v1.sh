#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core
export PYTHONPATH=src

echo "TEST_BR_CANDIDATE_POLICY_TABLE_V1_START"

python -m py_compile \
  src/scripts/analytics/build_br_candidate_policy_table_v1.py \
  src/scripts/analytics/build_br_governance_alpha_v2.py

python src/scripts/analytics/build_br_candidate_policy_table_v1.py \
  --window-days 30 \
  --min-closed-trades 5 \
  --min-governance-rows 5 | tee /tmp/br_candidate_policy_table_v1.out

grep -q "BR_POLICY_TABLE_V1" /tmp/br_candidate_policy_table_v1.out
grep -q "BR_POLICY_TABLE_ROW" /tmp/br_candidate_policy_table_v1.out
grep -q "BR_POLICY_TABLE_SUMMARY" /tmp/br_candidate_policy_table_v1.out
grep -q "BR_POLICY_TABLE_V1_OK" /tmp/br_candidate_policy_table_v1.out

echo "TEST_BR_CANDIDATE_POLICY_TABLE_V1_OK"
