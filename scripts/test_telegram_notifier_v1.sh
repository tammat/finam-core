#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core
export PYTHONPATH=src

echo "TEST_TELEGRAM_NOTIFIER_V1_START"

TMP_LOG="$(mktemp)"

TELEGRAM_NOTIFY_DRY_RUN=1 python - <<'PY' 2>&1 | tee "$TMP_LOG"
from finam_core.notifications.telegram_notifier_v1 import TelegramNotifierV1

notifier = TelegramNotifierV1(
    token="TEST_TOKEN",
    chat_id="TEST_CHAT",
)

result = notifier.send_text("Finam_Core TelegramNotifierV1 dry-run test")

assert result.dry_run is True
assert result.sent is False
assert result.chat_id == "TEST_CHAT"
assert result.text_len > 0
assert result.error is None

print("TELEGRAM_NOTIFIER_V1_PY_OK")
PY

grep -q "TELEGRAM_NOTIFY_DRY_RUN" "$TMP_LOG"
grep -q "TELEGRAM_NOTIFIER_V1_PY_OK" "$TMP_LOG"

echo "TEST_TELEGRAM_NOTIFIER_V1_OK"
