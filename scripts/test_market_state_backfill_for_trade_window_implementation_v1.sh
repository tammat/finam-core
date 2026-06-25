#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core || exit 1

echo "=== TEST_MARKET_STATE_BACKFILL_FOR_TRADE_WINDOW_IMPLEMENTATION_V1 ==="

python3 -m py_compile \
  src/scripts/research/build_market_state_backfill_for_trade_window_implementation_v1.py

PYTHONPATH=src \
src/scripts/research/build_market_state_backfill_for_trade_window_implementation_v1.py \
  | tee /tmp/market_state_backfill_for_trade_window_implementation_v1.out

grep -q "MARKET_STATE_BACKFILL_FOR_TRADE_WINDOW_IMPLEMENTATION_V1" /tmp/market_state_backfill_for_trade_window_implementation_v1.out
grep -q "source=public.feature_snapshots" /tmp/market_state_backfill_for_trade_window_implementation_v1.out
grep -q "target_symbol=BRN6@RTSX" /tmp/market_state_backfill_for_trade_window_implementation_v1.out
grep -q "target_timeframe=M5" /tmp/market_state_backfill_for_trade_window_implementation_v1.out
grep -q "snapshots_written=" /tmp/market_state_backfill_for_trade_window_implementation_v1.out
grep -q "db_update=1" /tmp/market_state_backfill_for_trade_window_implementation_v1.out
grep -q "VERDICT=MARKET_STATE_BACKFILL_FOR_TRADE_WINDOW_IMPLEMENTATION_OK" /tmp/market_state_backfill_for_trade_window_implementation_v1.out

echo "TEST_MARKET_STATE_BACKFILL_FOR_TRADE_WINDOW_IMPLEMENTATION_V1_OK"
