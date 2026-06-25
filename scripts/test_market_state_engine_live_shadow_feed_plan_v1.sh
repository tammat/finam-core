#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core || exit 1

echo "=== TEST_MARKET_STATE_ENGINE_LIVE_SHADOW_FEED_PLAN_V1 ==="

python3 -m py_compile \
  src/scripts/research/build_market_state_engine_live_shadow_feed_plan_v1.py

src/scripts/research/build_market_state_engine_live_shadow_feed_plan_v1.py \
  | tee /tmp/market_state_engine_live_shadow_feed_plan_v1.out

grep -q "MARKET_STATE_ENGINE_LIVE_SHADOW_FEED_PLAN_V1" /tmp/market_state_engine_live_shadow_feed_plan_v1.out
grep -q "mode=live_shadow_feed_plan_only" /tmp/market_state_engine_live_shadow_feed_plan_v1.out
grep -q "runtime_changed=0" /tmp/market_state_engine_live_shadow_feed_plan_v1.out
grep -q "execution_changed=0" /tmp/market_state_engine_live_shadow_feed_plan_v1.out
grep -q "real_trading_enabled=0" /tmp/market_state_engine_live_shadow_feed_plan_v1.out
grep -q "orders_sent=0" /tmp/market_state_engine_live_shadow_feed_plan_v1.out
grep -q "FLOW from=LiveMarketData to=market_event_copy" /tmp/market_state_engine_live_shadow_feed_plan_v1.out
grep -q "RULE name=live_feed_is_copy_only" /tmp/market_state_engine_live_shadow_feed_plan_v1.out
grep -q "RULE name=live_feed_writes_research_schema_only" /tmp/market_state_engine_live_shadow_feed_plan_v1.out
grep -q "FIELD name=symbol" /tmp/market_state_engine_live_shadow_feed_plan_v1.out
grep -q "VERDICT=MARKET_STATE_ENGINE_LIVE_SHADOW_FEED_PLAN_READY" /tmp/market_state_engine_live_shadow_feed_plan_v1.out

echo "TEST_MARKET_STATE_ENGINE_LIVE_SHADOW_FEED_PLAN_V1_OK"
