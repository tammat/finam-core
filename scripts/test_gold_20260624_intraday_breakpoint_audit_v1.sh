#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core || exit 1

echo "=== TEST_GOLD_20260624_INTRADAY_BREAKPOINT_AUDIT_V1 ==="

python3 -m py_compile \
  src/scripts/research/build_gold_20260624_intraday_breakpoint_audit_v1.py

src/scripts/research/build_gold_20260624_intraday_breakpoint_audit_v1.py \
  | tee /tmp/gold_20260624_intraday_breakpoint_audit_v1.out

grep -q "BREAKPOINT_ROW symbol=GDU6@RTSX mode=FULL_DAY" \
  /tmp/gold_20260624_intraday_breakpoint_audit_v1.out

grep -q "BREAKPOINT_ROW symbol=GDU6@RTSX mode=EXCLUDE_11_13_MSK" \
  /tmp/gold_20260624_intraday_breakpoint_audit_v1.out

grep -q "BREAKPOINT_ROW symbol=GLU6@RTSX mode=FULL_DAY" \
  /tmp/gold_20260624_intraday_breakpoint_audit_v1.out

grep -q "BREAKPOINT_ROW symbol=GLU6@RTSX mode=EXCLUDE_11_13_MSK" \
  /tmp/gold_20260624_intraday_breakpoint_audit_v1.out

grep -q "VERDICT=GOLD_20260624_INTRADAY_BREAKPOINT_AUDIT_READY" \
  /tmp/gold_20260624_intraday_breakpoint_audit_v1.out

echo "TEST_GOLD_20260624_INTRADAY_BREAKPOINT_AUDIT_V1_OK"
