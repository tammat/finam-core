#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core || exit 1

echo "=== TEST_MARKET_STATE_ENGINE_IMPLEMENTATION_PLAN_V1 ==="

python3 -m py_compile \
  src/scripts/research/build_market_state_engine_implementation_plan_v1.py

src/scripts/research/build_market_state_engine_implementation_plan_v1.py \
  | tee /tmp/market_state_engine_implementation_plan_v1.out

grep -q "MARKET_STATE_ENGINE_IMPLEMENTATION_PLAN_V1" /tmp/market_state_engine_implementation_plan_v1.out
grep -q "real_trading_enabled=0" /tmp/market_state_engine_implementation_plan_v1.out
grep -q "orders_sent=0" /tmp/market_state_engine_implementation_plan_v1.out
grep -q "FILE path=src/finam_core/research/market_state/engine.py" /tmp/market_state_engine_implementation_plan_v1.out
grep -q "STAGE code=STAGE_9_ENGINE" /tmp/market_state_engine_implementation_plan_v1.out
grep -q "CONTRACT name=does_not_read_pnl" /tmp/market_state_engine_implementation_plan_v1.out
grep -q "CONTRACT name=does_not_change_runtime" /tmp/market_state_engine_implementation_plan_v1.out
grep -q "TEST_REQUIREMENT name=engine_does_not_import_execution_modules" /tmp/market_state_engine_implementation_plan_v1.out
grep -q "GUARD name=no_order_client_import" /tmp/market_state_engine_implementation_plan_v1.out
grep -q "rule=engine_is_not_order_generator" /tmp/market_state_engine_implementation_plan_v1.out
grep -q "VERDICT=MARKET_STATE_ENGINE_IMPLEMENTATION_PLAN_READY" /tmp/market_state_engine_implementation_plan_v1.out

echo "TEST_MARKET_STATE_ENGINE_IMPLEMENTATION_PLAN_V1_OK"
