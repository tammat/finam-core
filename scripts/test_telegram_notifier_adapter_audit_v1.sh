#!/usr/bin/env bash
set -euo pipefail

cd "$(git rev-parse --show-toplevel)"

echo "=== TEST TELEGRAM NOTIFIER ADAPTER AUDIT V1 ==="
echo "runtime_allow=0"
echo "execution_enabled=0"
echo "real_trading_enabled=0"

python3 -m py_compile src/scripts/research/build_telegram_notifier_adapter_audit_v1.py

PYTHONPATH=src python3 src/scripts/research/build_telegram_notifier_adapter_audit_v1.py \
  | tee /tmp/telegram_notifier_adapter_audit_v1.log

grep -q "TELEGRAM_NOTIFIER_ADAPTER_AUDIT_V1_OK" /tmp/telegram_notifier_adapter_audit_v1.log
grep -q "TELEGRAM_NOTIFIER_ADAPTER_AUDIT_SUMMARY" /tmp/telegram_notifier_adapter_audit_v1.log
grep -q "telegram_send=0" /tmp/telegram_notifier_adapter_audit_v1.log
grep -q "db_update=0" /tmp/telegram_notifier_adapter_audit_v1.log
grep -q "VERDICT=" /tmp/telegram_notifier_adapter_audit_v1.log

echo "=== TELEGRAM NOTIFIER ADAPTER AUDIT SUMMARY ==="
grep -E "TELEGRAM_NOTIFIER_SOURCE_HIT|TELEGRAM_NOTIFIER_ENV_ROW|files_with_hits=|send_message_hits=|token_hits=|chat_hits=|notifier_class_hits=|telegram_env_keys=|VERDICT=" \
  /tmp/telegram_notifier_adapter_audit_v1.log | head -220

echo TEST_TELEGRAM_NOTIFIER_ADAPTER_AUDIT_V1_OK
