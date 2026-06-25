#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core || exit 1

echo "=== TEST_GLOBAL_MARKET_STATE_LINKING_V1 ==="

python3 -m py_compile \
  src/scripts/research/build_global_market_state_linking_v1.py

src/scripts/research/build_global_market_state_linking_v1.py \
  | tee /tmp/global_market_state_linking_v1.out

grep -q "GLOBAL_MARKET_STATE_LINKING_V1" /tmp/global_market_state_linking_v1.out
grep -q "linked_rows=" /tmp/global_market_state_linking_v1.out
grep -q "no_snapshot=" /tmp/global_market_state_linking_v1.out
grep -q "entry_only=" /tmp/global_market_state_linking_v1.out
grep -q "db_update=1" /tmp/global_market_state_linking_v1.out
grep -q "runtime_changed=0" /tmp/global_market_state_linking_v1.out
grep -q "execution_changed=0" /tmp/global_market_state_linking_v1.out
grep -q "real_trading_enabled=0" /tmp/global_market_state_linking_v1.out
grep -q "orders_sent=0" /tmp/global_market_state_linking_v1.out
grep -q "VERDICT=GLOBAL_MARKET_STATE_LINKING_OK" /tmp/global_market_state_linking_v1.out

echo "TEST_GLOBAL_MARKET_STATE_LINKING_V1_OK"
