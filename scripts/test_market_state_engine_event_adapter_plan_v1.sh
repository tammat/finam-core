#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core || exit 1

echo "=== TEST_MARKET_STATE_ENGINE_EVENT_ADAPTER_PLAN_V1 ==="

python3 -m py_compile \
src/scripts/research/build_market_state_engine_event_adapter_plan_v1.py

src/scripts/research/build_market_state_engine_event_adapter_plan_v1.py \
| tee /tmp/market_state_engine_event_adapter_plan_v1.out

grep -q "MARKET_STATE_ENGINE_EVENT_ADAPTER_PLAN_V1" /tmp/market_state_engine_event_adapter_plan_v1.out
grep -q "EVENT name=MarketStateBuiltEvent" /tmp/market_state_engine_event_adapter_plan_v1.out
grep -q "EVENT name=EdgeDiscoveredEvent" /tmp/market_state_engine_event_adapter_plan_v1.out
grep -q "EVENT name=StrategyRecommendedEvent" /tmp/market_state_engine_event_adapter_plan_v1.out
grep -q "RESPONSIBILITY name=subscribe_market_events" /tmp/market_state_engine_event_adapter_plan_v1.out
grep -q "rule=single_event_bus" /tmp/market_state_engine_event_adapter_plan_v1.out
grep -q "rule=research_uses_adapter" /tmp/market_state_engine_event_adapter_plan_v1.out
grep -q "VERDICT=MARKET_STATE_ENGINE_EVENT_ADAPTER_PLAN_READY" /tmp/market_state_engine_event_adapter_plan_v1.out

echo "TEST_MARKET_STATE_ENGINE_EVENT_ADAPTER_PLAN_V1_OK"
