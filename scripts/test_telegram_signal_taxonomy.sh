#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH="${PYTHONPATH:-src}"

python - <<'PY'
from finam_core.notifications.telegram_signal_taxonomy import (
    TelegramSignalMessage,
    format_telegram_signal_message,
)

msg = TelegramSignalMessage(
    channel_type="PAPER",
    symbol="BRM6@RTSX",
    display_name="Фьючерс Brent",
    direction="LONG",
    source="strategy",
    strategy="br_conservative_breakout",
    timeframe="M5",
    confidence=0.74,
    entry=100.5,
    stop=99.8,
    take=102.0,
    risk_comment="Портфельный перегрев HIGH, риск снижен.",
    reason="Пробой после сжатия.",
)

text = format_telegram_signal_message(msg)

assert "[PAPER][LONG]" in text
assert "Инструмент: BRM6@RTSX" in text
assert "Название: Фьючерс Brent" in text
assert "Уверенность: 74.0%" in text
assert "Риск:" in text
assert "Обоснование:" in text

print("TEST_TELEGRAM_SIGNAL_TAXONOMY_OK")
PY

python -m py_compile src/finam_core/notifications/telegram_signal_taxonomy.py
