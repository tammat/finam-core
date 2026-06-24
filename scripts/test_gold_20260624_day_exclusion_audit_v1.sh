#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core || exit 1

echo "=== TEST_GOLD_20260624_DAY_EXCLUSION_AUDIT_V1 ==="

python3 -m py_compile \
  src/scripts/research/build_gold_20260624_day_exclusion_audit_v1.py

src/scripts/research/build_gold_20260624_day_exclusion_audit_v1.py \
  | tee /tmp/gold_20260624_day_exclusion_audit_v1.out

grep -q "AUDIT_ROW symbol=GDU6@RTSX mode=FULL_FILTERED" \
  /tmp/gold_20260624_day_exclusion_audit_v1.out

grep -q "AUDIT_ROW symbol=GDU6@RTSX mode=EXCLUDE_2026_06_24" \
  /tmp/gold_20260624_day_exclusion_audit_v1.out

grep -q "AUDIT_ROW symbol=GLU6@RTSX mode=FULL_FILTERED" \
  /tmp/gold_20260624_day_exclusion_audit_v1.out

grep -q "AUDIT_ROW symbol=GLU6@RTSX mode=EXCLUDE_2026_06_24" \
  /tmp/gold_20260624_day_exclusion_audit_v1.out

grep -q "VERDICT=GOLD_20260624_DAY_EXCLUSION_AUDIT_READY" \
  /tmp/gold_20260624_day_exclusion_audit_v1.out

echo "TEST_GOLD_20260624_DAY_EXCLUSION_AUDIT_V1_OK"
