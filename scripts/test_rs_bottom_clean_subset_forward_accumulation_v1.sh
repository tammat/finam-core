#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_RS_BOTTOM_CLEAN_SUBSET_FORWARD_ACCUMULATION_V1 ==="

python3 -m py_compile src/scripts/research/build_rs_bottom_clean_subset_forward_accumulation_v1.py

python3 src/scripts/research/build_rs_bottom_clean_subset_forward_accumulation_v1.py \
  | tee /tmp/rs_bottom_clean_subset_forward_accumulation_v1.log

grep -q "ACCUMULATION_ROW" /tmp/rs_bottom_clean_subset_forward_accumulation_v1.log
grep -q "target_completed=100" /tmp/rs_bottom_clean_subset_forward_accumulation_v1.log
grep -q "real_pf=" /tmp/rs_bottom_clean_subset_forward_accumulation_v1.log
grep -q "decision=" /tmp/rs_bottom_clean_subset_forward_accumulation_v1.log
grep -q "VERDICT=RS_BOTTOM_CLEAN_SUBSET_FORWARD_ACCUMULATION_READY" /tmp/rs_bottom_clean_subset_forward_accumulation_v1.log

echo "VERDICT=RS_BOTTOM_CLEAN_SUBSET_FORWARD_ACCUMULATION_TEST_OK"
echo "TEST_RS_BOTTOM_CLEAN_SUBSET_FORWARD_ACCUMULATION_V1_OK"
