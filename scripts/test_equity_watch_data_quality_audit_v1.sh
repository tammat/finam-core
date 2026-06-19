#!/usr/bin/env bash
set -euo pipefail

cd "$(git rev-parse --show-toplevel)"

echo "=== TEST EQUITY WATCH DATA QUALITY AUDIT V1 ==="
echo "runtime_allow=0"
echo "execution_enabled=0"
echo "real_trading_enabled=0"
echo "orders_create=0"
echo "execution_intents_create=0"

python3 -m py_compile src/scripts/research/build_equity_watch_data_quality_audit_v1.py

PYTHONPATH=src \
RUNTIME_ALLOW_TRADING=0 EXECUTION_ENABLED=0 REAL_TRADING_ENABLED=0 \
python3 src/scripts/research/build_equity_watch_data_quality_audit_v1.py \
  | tee /tmp/equity_watch_data_quality_audit_v1.log

grep -q "EQUITY_WATCH_DATA_QUALITY_AUDIT_V1_OK" /tmp/equity_watch_data_quality_audit_v1.log
grep -q "symbol=OZON@MISX" /tmp/equity_watch_data_quality_audit_v1.log
grep -q "symbol=SBERP@MISX" /tmp/equity_watch_data_quality_audit_v1.log
grep -q "symbol=T@MISX" /tmp/equity_watch_data_quality_audit_v1.log
grep -q "orders_create=0" /tmp/equity_watch_data_quality_audit_v1.log
grep -q "execution_intents_create=0" /tmp/equity_watch_data_quality_audit_v1.log
grep -q "execution_enabled=0" /tmp/equity_watch_data_quality_audit_v1.log
grep -q "real_trading_enabled=0" /tmp/equity_watch_data_quality_audit_v1.log
grep -q "VERDICT=EQUITY_WATCH_DATA_QUALITY_AUDIT_READY" /tmp/equity_watch_data_quality_audit_v1.log

echo "=== EQUITY WATCH DATA QUALITY SUMMARY ==="
grep -E "EQUITY_DATA_ROW|RUNTIME_ROW|BARS_ROW|HISTORY_ROW|LATEST_STATUS_ROW|VERDICT=" \
  /tmp/equity_watch_data_quality_audit_v1.log

echo TEST_EQUITY_WATCH_DATA_QUALITY_AUDIT_V1_OK
