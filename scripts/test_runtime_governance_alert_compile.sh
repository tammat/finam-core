#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH="${PYTHONPATH:-src}"

python -m py_compile \
  src/scripts/send_runtime_governance_alert.py \
  src/finam_core/notifications/telegram_signal_taxonomy.py \
  src/finam_core/notifications/telegram_signal_router.py \
  src/finam_core/notifications/telegram_signal_dispatcher.py \
  src/finam_core/runtime/runtime_governance_coordinator_v2.py

echo "TEST_RUNTIME_GOVERNANCE_ALERT_COMPILE_OK"
