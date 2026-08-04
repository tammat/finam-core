#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH="${PYTHONPATH:-src}"

python - <<'PY'
import os
from unittest.mock import patch

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

radar = TelegramSignalMessage(
    channel_type="RADAR",
    symbol="BTCUSD",
    display_name="Bitcoin / USD",
    direction="CONTEXT",
    source="test",
    strategy="btc_shadow_context",
    timeframe="M5",
    confidence=0.7,
)
managed_env = {
    "TELEGRAM_BOT_TOKEN": None,
    "TELEGRAM_MARKET_RADAR_CHAT_ID": None,
    "TELEGRAM_PROXY": None,
    "TG_BOT_TOKEN": None,
    "TG_CHAT_ID": None,
    "TG_ALERT_BOT_TOKEN": "test-token",
    "TG_ALERT_CHAT": "test-chat",
    "TG_PROXY": "socks5h://127.0.0.1:1080",
}

saved_env = {
    key: os.environ.get(key)
    for key in managed_env
}

try:
    for key, value in managed_env.items():
        if value is None:
            os.environ.pop(key, None)
        else:
            os.environ[key] = value

    with patch(
        "finam_core.notifications.telegram_signal_dispatcher.requests.post"
    ) as post:
        post.return_value.raise_for_status.return_value = None
        r3 = dispatcher.dispatch(radar)

    assert r3.status == "SENT"
    assert r3.chat_id == "test-chat"
    assert post.call_args.kwargs["json"]["chat_id"] == "test-chat"
    assert (
        post.call_args.kwargs["proxies"]["https"]
        == "socks5h://127.0.0.1:1080"
    )
finally:
    for key, value in saved_env.items():
        if value is None:
            os.environ.pop(key, None)
        else:
            os.environ[key] = value

print("TEST_TELEGRAM_SIGNAL_DISPATCHER_OK")
PY

python -m py_compile \
  src/finam_core/notifications/telegram_signal_taxonomy.py \
  src/finam_core/notifications/telegram_signal_router.py \
  src/finam_core/notifications/telegram_signal_dispatcher.py
