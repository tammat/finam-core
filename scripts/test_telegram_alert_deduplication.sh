#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH="${PYTHONPATH:-src}"

python -m py_compile src/finam_core/notifications/telegram_alert_deduplication.py

python - <<'PY'
from finam_core.notifications.telegram_alert_deduplication import (
    TelegramAlertDedupDecision,
)

d = TelegramAlertDedupDecision(
    should_send=True,
    alert_key="portfolio_heat:HIGH",
    reason="первое_сообщение_по_ключу",
)

assert d.should_send is True
assert d.alert_key == "portfolio_heat:HIGH"

print("TEST_TELEGRAM_ALERT_DEDUPLICATION_OK")
PY
