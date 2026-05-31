#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core
export PYTHONPATH=src

echo "TEST_ACCUMULATION_PLAN_NG_TRACKING_V1_START"

python -m py_compile src/scripts/analytics/build_accumulation_plan_v1.py

python src/scripts/analytics/build_accumulation_plan_v1.py | tee /tmp/accumulation_plan_ng_tracking_v1.out

grep -q "underlying=NATURAL_GAS" /tmp/accumulation_plan_ng_tracking_v1.out
grep -q "symbol=NGN6@RTSX" /tmp/accumulation_plan_ng_tracking_v1.out
grep -q "strategy=NG_CONSERVATIVE_BREAKOUT_M1" /tmp/accumulation_plan_ng_tracking_v1.out
grep -q "action=CONTINUE_PAPER_ACCUMULATION" /tmp/accumulation_plan_ng_tracking_v1.out

echo "TEST_ACCUMULATION_PLAN_NG_TRACKING_V1_OK"
