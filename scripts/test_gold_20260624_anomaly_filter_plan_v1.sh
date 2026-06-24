#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core || exit 1

echo "=== TEST_GOLD_20260624_ANOMALY_FILTER_PLAN_V1 ==="

python3 -m py_compile \
  src/scripts/research/build_gold_20260624_anomaly_filter_plan_v1.py

src/scripts/research/build_gold_20260624_anomaly_filter_plan_v1.py \
  | tee /tmp/gold_20260624_anomaly_filter_plan_v1.out

grep -q "GOLD_20260624_ANOMALY_FILTER_PLAN_V1" \
  /tmp/gold_20260624_anomaly_filter_plan_v1.out

grep -q "H1=ONE_DAY_ANOMALY" \
  /tmp/gold_20260624_anomaly_filter_plan_v1.out

grep -q "H2=INTRADAY_BREAKPOINT" \
  /tmp/gold_20260624_anomaly_filter_plan_v1.out

grep -q "VERDICT=GOLD_20260624_ANOMALY_FILTER_PLAN_READY" \
  /tmp/gold_20260624_anomaly_filter_plan_v1.out

echo "TEST_GOLD_20260624_ANOMALY_FILTER_PLAN_V1_OK"
