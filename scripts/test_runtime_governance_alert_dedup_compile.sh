#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH="${PYTHONPATH:-src}"

python -m py_compile \
  src/finam_core/notifications/telegram_alert_deduplication.py \
  src/scripts/send_runtime_governance_alert.py

grep -q "RUNTIME_GOVERNANCE_ALERT_DEDUP_SKIPPED" src/scripts/send_runtime_governance_alert.py
grep -q "TelegramAlertDeduplicator" src/scripts/send_runtime_governance_alert.py

echo "TEST_RUNTIME_GOVERNANCE_ALERT_DEDUP_COMPILE_OK"
