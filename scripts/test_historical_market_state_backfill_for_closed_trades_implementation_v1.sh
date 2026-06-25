#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core || exit 1

echo "=== TEST_HISTORICAL_MARKET_STATE_BACKFILL_FOR_CLOSED_TRADES_IMPLEMENTATION_V1 ==="

python3 -m py_compile \
  src/scripts/research/build_historical_market_state_backfill_for_closed_trades_implementation_v1.py

PYTHONPATH=src \
src/scripts/research/build_historical_market_state_backfill_for_closed_trades_implementation_v1.py \
  | tee /tmp/historical_market_state_backfill_for_closed_trades_implementation_v1.out

grep -q "HISTORICAL_MARKET_STATE_BACKFILL_FOR_CLOSED_TRADES_IMPLEMENTATION_V1" /tmp/historical_market_state_backfill_for_closed_trades_implementation_v1.out
grep -q "target_source=market_state_backfill_closed_trades_v1" /tmp/historical_market_state_backfill_for_closed_trades_implementation_v1.out
grep -q "snapshots_written=" /tmp/historical_market_state_backfill_for_closed_trades_implementation_v1.out
grep -q "db_update=1" /tmp/historical_market_state_backfill_for_closed_trades_implementation_v1.out
grep -q "runtime_changed=0" /tmp/historical_market_state_backfill_for_closed_trades_implementation_v1.out
grep -q "execution_changed=0" /tmp/historical_market_state_backfill_for_closed_trades_implementation_v1.out
grep -q "real_trading_enabled=0" /tmp/historical_market_state_backfill_for_closed_trades_implementation_v1.out
grep -q "orders_sent=0" /tmp/historical_market_state_backfill_for_closed_trades_implementation_v1.out
grep -q "VERDICT=HISTORICAL_MARKET_STATE_BACKFILL_FOR_CLOSED_TRADES_IMPLEMENTATION_OK" /tmp/historical_market_state_backfill_for_closed_trades_implementation_v1.out

echo "TEST_HISTORICAL_MARKET_STATE_BACKFILL_FOR_CLOSED_TRADES_IMPLEMENTATION_V1_OK"
