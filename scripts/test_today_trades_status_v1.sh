#!/usr/bin/env bash
set -euo pipefail

cd "$(git rev-parse --show-toplevel)"

echo "=== TEST TODAY TRADES STATUS V1 ==="
echo "runtime_allow=0"
echo "execution_enabled=0"
echo "real_trading_enabled=0"

python3 -m py_compile src/scripts/runtime/build_today_trades_status_v1.py

PYTHONPATH=src python3 src/scripts/runtime/build_today_trades_status_v1.py \
  | tee /tmp/today_trades_status_v1.log

grep -q "TODAY_TRADES_STATUS_V1_OK" /tmp/today_trades_status_v1.log
grep -q "TODAY_TRADES_SUMMARY" /tmp/today_trades_status_v1.log
grep -q "TODAY_TRADES_BY_SYMBOL" /tmp/today_trades_status_v1.log
grep -q "TODAY_TRADES_STATUS_SUMMARY" /tmp/today_trades_status_v1.log
grep -q "db_update=0" /tmp/today_trades_status_v1.log
grep -q "VERDICT=" /tmp/today_trades_status_v1.log

echo
echo "=== TODAY TRADES STATUS SUMMARY ==="
grep -E "trades_today=|strategy_missing=|timeframe_missing=|continuous_symbol_missing=|TODAY_TRADES_SYMBOL_ROW|symbols=|total_net_pnl=|context_clean=|VERDICT=" \
  /tmp/today_trades_status_v1.log

echo TEST_TODAY_TRADES_STATUS_V1_OK
