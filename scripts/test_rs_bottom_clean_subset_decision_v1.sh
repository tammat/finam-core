#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_RS_BOTTOM_CLEAN_SUBSET_DECISION_V1 ==="

python3 -m py_compile src/scripts/research/build_rs_bottom_clean_subset_decision_v1.py

python3 src/scripts/research/build_rs_bottom_clean_subset_decision_v1.py \
  | tee /tmp/rs_bottom_clean_subset_decision_v1.log

grep -q "RS_BOTTOM_CURRENT_VERSION_REJECTED value=1" /tmp/rs_bottom_clean_subset_decision_v1.log
grep -q "RS_BOTTOM_CLEAN_SUBSET_RESEARCH_CANDIDATE value=1" /tmp/rs_bottom_clean_subset_decision_v1.log
grep -q "NG_EXCLUDED value=1" /tmp/rs_bottom_clean_subset_decision_v1.log
grep -q "COMPRESSION_RANGE_EXCLUDED value=1" /tmp/rs_bottom_clean_subset_decision_v1.log
grep -q "MSK_12H_EXCLUDED value=1" /tmp/rs_bottom_clean_subset_decision_v1.log
grep -q "REAL_TRADING_ALLOWED value=0" /tmp/rs_bottom_clean_subset_decision_v1.log
grep -q "VERDICT=RS_BOTTOM_CLEAN_SUBSET_DECISION_READY" /tmp/rs_bottom_clean_subset_decision_v1.log

echo "VERDICT=RS_BOTTOM_CLEAN_SUBSET_DECISION_TEST_OK"
echo "TEST_RS_BOTTOM_CLEAN_SUBSET_DECISION_V1_OK"
