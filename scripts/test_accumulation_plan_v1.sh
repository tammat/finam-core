#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core
export PYTHONPATH=src

echo "TEST_ACCUMULATION_PLAN_V1_START"

python -m py_compile src/scripts/analytics/build_accumulation_plan_v1.py

python src/scripts/analytics/build_accumulation_plan_v1.py \
  | tee /tmp/accumulation_plan_v1.out

grep -q "ACCUMULATION_PLAN_V1" /tmp/accumulation_plan_v1.out
grep -q "ACCUMULATION_PLAN_ROW" /tmp/accumulation_plan_v1.out
grep -q "ACCUMULATION_PLAN_SUMMARY" /tmp/accumulation_plan_v1.out
grep -q "ACCUMULATION_PLAN_V1_OK" /tmp/accumulation_plan_v1.out

echo "TEST_ACCUMULATION_PLAN_V1_OK"
