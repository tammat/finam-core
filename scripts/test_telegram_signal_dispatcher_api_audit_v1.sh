#!/usr/bin/env bash
set -euo pipefail

cd "$(git rev-parse --show-toplevel)"

echo "=== TEST TELEGRAM SIGNAL DISPATCHER API AUDIT V1 ==="
echo "runtime_allow=0"
echo "execution_enabled=0"
echo "real_trading_enabled=0"

python3 -m py_compile src/scripts/research/build_telegram_signal_dispatcher_api_audit_v1.py

PYTHONPATH=src python3 src/scripts/research/build_telegram_signal_dispatcher_api_audit_v1.py \
  | tee /tmp/telegram_signal_dispatcher_api_audit_v1.log

grep -q "TELEGRAM_SIGNAL_DISPATCHER_API_AUDIT_V1_OK" /tmp/telegram_signal_dispatcher_api_audit_v1.log
grep -q "TELEGRAM_SIGNAL_DISPATCHER_API_AUDIT_SUMMARY" /tmp/telegram_signal_dispatcher_api_audit_v1.log
grep -q "TELEGRAM_SIGNAL_API_FIELD" /tmp/telegram_signal_dispatcher_api_audit_v1.log
grep -q "telegram_send=0" /tmp/telegram_signal_dispatcher_api_audit_v1.log
grep -q "db_update=0" /tmp/telegram_signal_dispatcher_api_audit_v1.log
grep -q "VERDICT=" /tmp/telegram_signal_dispatcher_api_audit_v1.log

echo "=== TELEGRAM SIGNAL DISPATCHER API SUMMARY ==="
grep -E "TELEGRAM_SIGNAL_API_FIELD|TELEGRAM_SIGNAL_API_SOURCE_ROW|class_hits=|VERDICT=" \
  /tmp/telegram_signal_dispatcher_api_audit_v1.log | head -180

echo TEST_TELEGRAM_SIGNAL_DISPATCHER_API_AUDIT_V1_OK
