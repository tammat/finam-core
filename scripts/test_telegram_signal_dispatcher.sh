#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH="${PYTHONPATH:-src}"

python - <<'PY'
from finam_core.notifications.telegram_signal_dispatcher import TelegramSignalDispatcher
from finam_core.notifications.telegram_signal_taxonomy import TelegramSignalMessage

dispatcher = TelegramSignalDispatcher()

low_conf = TelegramSignalMessage(
    channel_type="PAPER",
    symbol="BRM6@RTSX",
    display_name="Фьючерс Brent",
    direction="LONG",
    source="strategy",
    strategy="br_conservative_breakout",
    timeframe="M5",
    confidence=0.5,
)

r = dispatcher.dispatch(low_conf)
assert r.status == "SKIPPED"
assert "ниже_порога" in r.reason

risk = TelegramSignalMessage(
    channel_type="RISK",
    symbol="BRM6@RTSX",
    display_name="Фьючерс Brent",
    direction="WARNING",
    source="governance",
    strategy="runtime_governance",
    timeframe="M5",
    confidence=0.0,
    risk_comment="Проверка без токена.",
)

r2 = dispatcher.dispatch(risk)
assert r2.status in {"SKIPPED", "ERROR"}
assert r2.target_env == "TELEGRAM_REAL_DESK_CHAT_ID"

print("TEST_TELEGRAM_SIGNAL_DISPATCHER_OK")
PY

python -m py_compile \
  src/finam_core/notifications/telegram_signal_taxonomy.py \
  src/finam_core/notifications/telegram_signal_router.py \
  src/finam_core/notifications/telegram_signal_dispatcher.py
