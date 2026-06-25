#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core || exit 1

echo "=== TEST_HISTORICAL_TRADE_LINKING_TO_MARKET_STATE_V1 ==="

python3 -m py_compile \
  src/scripts/research/build_historical_trade_linking_to_market_state_v1.py

src/scripts/research/build_historical_trade_linking_to_market_state_v1.py \
  | tee /tmp/historical_trade_linking_to_market_state_v1.out

grep -q "HISTORICAL_TRADE_LINKING_TO_MARKET_STATE_V1" /tmp/historical_trade_linking_to_market_state_v1.out
grep -q "linked_rows=" /tmp/historical_trade_linking_to_market_state_v1.out
grep -q "db_update=1" /tmp/historical_trade_linking_to_market_state_v1.out
grep -q "runtime_changed=0" /tmp/historical_trade_linking_to_market_state_v1.out
grep -q "execution_changed=0" /tmp/historical_trade_linking_to_market_state_v1.out
grep -q "real_trading_enabled=0" /tmp/historical_trade_linking_to_market_state_v1.out
grep -q "orders_sent=0" /tmp/historical_trade_linking_to_market_state_v1.out
grep -q "VERDICT=HISTORICAL_TRADE_LINKING_TO_MARKET_STATE_OK" /tmp/historical_trade_linking_to_market_state_v1.out

echo "TEST_HISTORICAL_TRADE_LINKING_TO_MARKET_STATE_V1_OK"
