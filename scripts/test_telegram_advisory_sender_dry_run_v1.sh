#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core
export PYTHONPATH=src

echo "TEST_TELEGRAM_ADVISORY_SENDER_DRY_RUN_V1_START"

TMP_LOG="$(mktemp)"

python - <<'PY' 2>&1 | tee "$TMP_LOG"
from finam_core.notifications.telegram_advisory_sender_dry_run_v1 import TelegramAdvisorySenderDryRunV1

sender = TelegramAdvisorySenderDryRunV1(chat_id="TEST_DRY_RUN_CHAT")

result = sender.send(
    symbol="BRN6@RTSX",
    severity="INFO",
    category="MANUAL_POSITION",
    text="BRN6 SHORT advisory dry-run",
)

assert result.dry_run is True
assert result.sent is False
assert result.chat_id == "TEST_DRY_RUN_CHAT"
assert result.symbol == "BRN6@RTSX"

print("TELEGRAM_ADVISORY_SENDER_DRY_RUN_V1_PY_OK")
PY

grep -q "TELEGRAM_ADVISORY_DRY_RUN_SEND" "$TMP_LOG"
grep -q "TELEGRAM_ADVISORY_SENDER_DRY_RUN_V1_PY_OK" "$TMP_LOG"

echo "TEST_TELEGRAM_ADVISORY_SENDER_DRY_RUN_V1_OK"
