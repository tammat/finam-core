#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core || exit 1

echo "=== TEST_MARKET_STATE_TRADE_LINKING_PLAN_V1 ==="

python3 -m py_compile \
  src/scripts/research/build_market_state_trade_linking_plan_v1.py

src/scripts/research/build_market_state_trade_linking_plan_v1.py \
  | tee /tmp/market_state_trade_linking_plan_v1.out

grep -q "MARKET_STATE_TRADE_LINKING_PLAN_V1" /tmp/market_state_trade_linking_plan_v1.out
grep -q "purpose=link_market_state_snapshots_to_clean_trade_facts" /tmp/market_state_trade_linking_plan_v1.out
grep -q "INPUT name=research.market_state_snapshots_v1" /tmp/market_state_trade_linking_plan_v1.out
grep -q "LINK_RULE name=link_trade_entry_to_nearest_prior_snapshot" /tmp/market_state_trade_linking_plan_v1.out
grep -q "LINK_RULE name=do_not_link_historical_replay_to_micro_live_layer" /tmp/market_state_trade_linking_plan_v1.out
grep -q "TABLE name=research.trade_state_snapshots_v1" /tmp/market_state_trade_linking_plan_v1.out
grep -q "QUALITY code=EXACT_OR_NEAREST_OK" /tmp/market_state_trade_linking_plan_v1.out
grep -q "GUARD name=clean_trade_source_filter_required" /tmp/market_state_trade_linking_plan_v1.out
grep -q "VERDICT=MARKET_STATE_TRADE_LINKING_PLAN_READY" /tmp/market_state_trade_linking_plan_v1.out

echo "TEST_MARKET_STATE_TRADE_LINKING_PLAN_V1_OK"
