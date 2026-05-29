#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core
export PYTHONPATH=src
export TELEGRAM_ACTIONABLE_ONLY=1

echo "TEST_TELEGRAM_ACTIONABLE_FILTER_V1_START"

python -m py_compile \
  src/finam_core/notifications/telegram_actionable_filter_v1.py \
  src/finam_core/notifications/telegram_notifier.py \
  src/finam_core/notifications/trade_signal_notifier.py

python - <<'PY'
from finam_core.notifications.telegram_actionable_filter_v1 import TelegramActionableFilterV1

f = TelegramActionableFilterV1()

allowed = [
    "REAL_ENTRY_SIGNAL BR вход=93.20 стоп=92.80 тейк=94.10",
    "Активная ручная сделка BR: подтянуть стоп",
    "Стоп-лосс достигнут BR",
    "Тейк-профит достигнут BR",
]

blocked = [
    "RUNTIME_GOVERNANCE_POPULATION_STATUS total_rows=22",
    "REGIME trend=flat vol=normal",
    "PIPE_SESSION_BLOCK phase=preopen",
    "WATCHLIST_TELEGRAM_SENT",
    "GRAFANA alert",
    "обычный технический лог",
]

for text in allowed:
    if not f.allows(text):
        raise SystemExit(f"EXPECTED_ALLOWED text={text!r} reason={f.reason(text)}")

for text in blocked:
    if f.allows(text):
        raise SystemExit(f"EXPECTED_BLOCKED text={text!r} reason={f.reason(text)}")

print("TELEGRAM_ACTIONABLE_FILTER_ASSERTIONS_OK")
PY

grep -Rni "TELEGRAM_ACTIONABLE_FILTER_DROP" \
  src/finam_core/notifications/telegram_notifier.py \
  src/finam_core/notifications/trade_signal_notifier.py

echo "TEST_TELEGRAM_ACTIONABLE_FILTER_V1_OK"
