#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core
export PYTHONPATH=src

echo "TEST_TELEGRAM_ADVISORY_FORMATTER_V1_START"

python -m py_compile src/finam_core/notifications/telegram_advisory_formatter_v1.py

python - <<'PY'
from finam_core.notifications.telegram_advisory_formatter_v1 import TelegramAdvisoryFormatterV1

formatter = TelegramAdvisoryFormatterV1()

msg = formatter.format_position_advisory(
    symbol="BRN6@RTSX",
    asset_class="FUTURES",
    side="SHORT",
    qty=-1.0,
    entry=95.09,
    current=94.93,
    pnl=113.44,
    pnl_day=0.0,
    stop=96.0692,
    take=92.5568,
    action="HOLD_PROFIT",
)

rendered = formatter.render(msg)

assert msg.severity == "INFO"
assert msg.category == "MANUAL_POSITION"
assert "BRN6@RTSX" in rendered
assert "удерживать прибыль" in rendered

print("TELEGRAM_ADVISORY_FORMATTER_V1_PY_OK")
PY

echo "TEST_TELEGRAM_ADVISORY_FORMATTER_V1_OK"
