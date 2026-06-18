#!/usr/bin/env bash
set -euo pipefail

cd "$(git rev-parse --show-toplevel)"

echo "=== TEST TODAY CLOSED PNL STATUS V1 ==="
echo "runtime_allow=0"
echo "execution_enabled=0"
echo "real_trading_enabled=0"

python3 -m py_compile src/scripts/runtime/build_today_closed_pnl_status_v1.py

PYTHONPATH=src python3 src/scripts/runtime/build_today_closed_pnl_status_v1.py \
  | tee /tmp/today_closed_pnl_status_v1.log

grep -q "TODAY_CLOSED_PNL_STATUS_V1_OK" /tmp/today_closed_pnl_status_v1.log
grep -q "TODAY_CLOSED_PNL_SUMMARY" /tmp/today_closed_pnl_status_v1.log
grep -q "TODAY_CLOSED_PNL_BY_SYMBOL" /tmp/today_closed_pnl_status_v1.log
grep -q "TODAY_CLOSED_PNL_STATUS_SUMMARY" /tmp/today_closed_pnl_status_v1.log
grep -q "db_update=0" /tmp/today_closed_pnl_status_v1.log
grep -q "VERDICT=" /tmp/today_closed_pnl_status_v1.log

echo
echo "=== TODAY CLOSED PNL STATUS SUMMARY ==="
grep -E "trades_today=|symbols=|closed_cycles=|gross_pnl=|commission=|net_pnl=|context_clean=|TODAY_CLOSED_PNL_SYMBOL_ROW|VERDICT=" \
  /tmp/today_closed_pnl_status_v1.log

echo TEST_TODAY_CLOSED_PNL_STATUS_V1_OK
