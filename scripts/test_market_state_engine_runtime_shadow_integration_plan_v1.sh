#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core || exit 1

echo "=== TEST_MARKET_STATE_ENGINE_RUNTIME_SHADOW_INTEGRATION_PLAN_V1 ==="

python3 -m py_compile \
src/scripts/research/build_market_state_engine_runtime_shadow_integration_plan_v1.py

src/scripts/research/build_market_state_engine_runtime_shadow_integration_plan_v1.py \
| tee /tmp/market_state_engine_runtime_shadow_integration_plan_v1.out

grep -q "MARKET_STATE_ENGINE_RUNTIME_SHADOW_INTEGRATION_PLAN_V1" \
/tmp/market_state_engine_runtime_shadow_integration_plan_v1.out

grep -q "FLOW from=MarketDataEvent to=Runtime Event Bus" \
/tmp/market_state_engine_runtime_shadow_integration_plan_v1.out

grep -q "COMPONENT name=RuntimeShadowSubscriber" \
/tmp/market_state_engine_runtime_shadow_integration_plan_v1.out

grep -q "RULE name=shadow_never_sends_orders" \
/tmp/market_state_engine_runtime_shadow_integration_plan_v1.out

grep -q "RULE name=shadow_processing_is_async" \
/tmp/market_state_engine_runtime_shadow_integration_plan_v1.out

grep -q "VERDICT=MARKET_STATE_ENGINE_RUNTIME_SHADOW_INTEGRATION_PLAN_READY" \
/tmp/market_state_engine_runtime_shadow_integration_plan_v1.out

echo "TEST_MARKET_STATE_ENGINE_RUNTIME_SHADOW_INTEGRATION_PLAN_V1_OK"
