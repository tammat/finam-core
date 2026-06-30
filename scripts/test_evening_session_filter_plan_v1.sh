#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core || exit 1

echo "=== TEST_EVENING_SESSION_FILTER_PLAN_V1 ==="

python3 -m py_compile \
  src/scripts/research/build_evening_session_filter_plan_v1.py

src/scripts/research/build_evening_session_filter_plan_v1.py \
  | tee /tmp/evening_session_filter_plan_v1.out

grep -q "FILTER_ROW symbol=GDU6@RTSX" /tmp/evening_session_filter_plan_v1.out
grep -q "FILTER_ROW symbol=GLU6@RTSX" /tmp/evening_session_filter_plan_v1.out
grep -q "VERDICT=EVENING_SESSION_FILTER_PLAN_READY" /tmp/evening_session_filter_plan_v1.out

echo "TEST_EVENING_SESSION_FILTER_PLAN_V1_OK"
