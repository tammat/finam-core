#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core || exit 1

echo "=== TEST_MICRO_LIVE_PREPARATION_V1 ==="

python3 -m py_compile \
  src/scripts/research/build_micro_live_preparation_v1.py

src/scripts/research/build_micro_live_preparation_v1.py \
  | tee /tmp/micro_live_preparation_v1.out

grep -q "MICRO_LIVE_PREPARATION_V1" /tmp/micro_live_preparation_v1.out
grep -q "real_trading_enabled=0" /tmp/micro_live_preparation_v1.out
grep -q "orders_sent=0" /tmp/micro_live_preparation_v1.out
grep -q "GATE code=EDGE_CANDIDATE_REQUIRED status=BLOCKING" /tmp/micro_live_preparation_v1.out
grep -q "GATE code=KILL_SWITCH_REQUIRED status=BLOCKING" /tmp/micro_live_preparation_v1.out
grep -q "LIMIT name=max_active_instruments value=1" /tmp/micro_live_preparation_v1.out
grep -q "EVIDENCE name=expectancy_positive_after_commission" /tmp/micro_live_preparation_v1.out
grep -q "contract=micro_live_cannot_be_enabled_by_research_script" /tmp/micro_live_preparation_v1.out
grep -q "rule=no_real_trading_without_edge" /tmp/micro_live_preparation_v1.out
grep -q "blocker=NO_CONFIRMED_EDGE_CANDIDATE_YET" /tmp/micro_live_preparation_v1.out
grep -q "VERDICT=MICRO_LIVE_PREPARATION_PLAN_READY_NOT_ENABLED" /tmp/micro_live_preparation_v1.out

echo "TEST_MICRO_LIVE_PREPARATION_V1_OK"
