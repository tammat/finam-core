#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core || exit 1

echo "=== TEST_MARKET_STATE_BACKFILL_FOR_TRADE_WINDOW_PLAN_V1 ==="

python3 -m py_compile \
  src/scripts/research/build_market_state_backfill_for_trade_window_plan_v1.py

src/scripts/research/build_market_state_backfill_for_trade_window_plan_v1.py \
  | tee /tmp/market_state_backfill_for_trade_window_plan_v1.out

grep -q "MARKET_STATE_BACKFILL_FOR_TRADE_WINDOW_PLAN_V1" /tmp/market_state_backfill_for_trade_window_plan_v1.out
grep -q "target_symbol=BRN6@RTSX" /tmp/market_state_backfill_for_trade_window_plan_v1.out
grep -q "target_timeframe=M5" /tmp/market_state_backfill_for_trade_window_plan_v1.out
grep -q "source=market_bars" /tmp/market_state_backfill_for_trade_window_plan_v1.out
grep -q "STEP name=run_market_state_engine" /tmp/market_state_backfill_for_trade_window_plan_v1.out
grep -q "GUARD name=no_runtime_write" /tmp/market_state_backfill_for_trade_window_plan_v1.out
grep -q "next=MARKET_STATE_BACKFILL_SOURCE_DIAGNOSTIC_V1" /tmp/market_state_backfill_for_trade_window_plan_v1.out
grep -q "VERDICT=MARKET_STATE_BACKFILL_FOR_TRADE_WINDOW_PLAN_READY" /tmp/market_state_backfill_for_trade_window_plan_v1.out

echo "TEST_MARKET_STATE_BACKFILL_FOR_TRADE_WINDOW_PLAN_V1_OK"
