#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core || exit 1

echo "=== TEST_MARKET_STATE_TRADE_LINKING_VALIDATION_V1_1 ==="

python3 -m py_compile \
  src/scripts/research/build_market_state_trade_linking_validation_v1.py

src/scripts/research/build_market_state_trade_linking_validation_v1.py \
  | tee /tmp/market_state_trade_linking_validation_v1_1.out

grep -q "MARKET_STATE_TRADE_LINKING_VALIDATION_V1" /tmp/market_state_trade_linking_validation_v1_1.out
grep -q "linked_total=44" /tmp/market_state_trade_linking_validation_v1_1.out
grep -q "link_ok=44" /tmp/market_state_trade_linking_validation_v1_1.out
grep -q "no_snapshot=0" /tmp/market_state_trade_linking_validation_v1_1.out
grep -q "duplicates=0" /tmp/market_state_trade_linking_validation_v1_1.out
grep -q "VERDICT=MARKET_STATE_TRADE_LINKING_VALIDATION_OK" /tmp/market_state_trade_linking_validation_v1_1.out

echo "TEST_MARKET_STATE_TRADE_LINKING_VALIDATION_V1_1_OK"
