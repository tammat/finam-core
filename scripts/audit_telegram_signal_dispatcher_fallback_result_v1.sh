#!/usr/bin/env bash
set -euo pipefail

ROOT="/opt/finam-core"
PYTHON="$ROOT/venv/bin/python"

echo "=== AUDIT TELEGRAM SIGNAL DISPATCHER FALLBACK RESULT V1 ==="

PYTHONPATH="$ROOT/src" "$PYTHON" - <<'PY'
from __future__ import annotations

import os
from unittest.mock import patch

from finam_core.notifications.telegram_signal_dispatcher import (
    TelegramSignalDispatcher,
)
from finam_core.notifications.telegram_signal_taxonomy import (
    TelegramSignalMessage,
)


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

saved = {
    key: os.environ.get(key)
    for key in managed_env
}

try:
    for key, value in managed_env.items():
        if value is None:
            os.environ.pop(key, None)
        else:
            os.environ[key] = value

    dispatcher = TelegramSignalDispatcher()

    with patch(
        "finam_core.notifications.telegram_signal_dispatcher.requests.post"
    ) as post:
        post.return_value.raise_for_status.return_value = None

        result = dispatcher.dispatch(radar)

    print(f"result_status={result.status}")
    print(f"result_chat_id={result.chat_id!r}")
    print(f"result_target_env={result.target_env!r}")
    print(f"result_reason={result.reason!r}")
    print(f"http_called={int(post.called)}")

    if post.called:
        kwargs = post.call_args.kwargs
        payload = kwargs.get("json") or {}
        proxies = kwargs.get("proxies") or {}

        print(f"http_chat_id={payload.get('chat_id')!r}")
        print(f"http_proxy_https={proxies.get('https')!r}")
        print(f"http_timeout={kwargs.get('timeout')!r}")

    expected_chat_id = "test-chat"

    if result.status != "SENT":
        classification = "DISPATCH_NOT_SENT"
    elif result.chat_id != expected_chat_id:
        classification = "RESULT_CHAT_ID_NOT_EFFECTIVE_CHAT_ID"
    elif not post.called:
        classification = "HTTP_TRANSPORT_NOT_CALLED"
    else:
        classification = "FALLBACK_RESULT_CONTRACT_OK"

    print(f"classification={classification}")

finally:
    for key, value in saved.items():
        if value is None:
            os.environ.pop(key, None)
        else:
            os.environ[key] = value

print("writes_performed=0")
print("runtime_changed=0")
print("execution_changed=0")
print("orders_changed=0")
print("fills_changed=0")
print("micro_live_allowed=0")
print("VERDICT=TELEGRAM_SIGNAL_DISPATCHER_FALLBACK_RESULT_V1_AUDITED")
PY
