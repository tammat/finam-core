#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python - <<'PY'
from finam_core.notifications.trade_signal_notifier import TradeSignalNotifier

n = TradeSignalNotifier()

print("enabled=", n.enabled)
print("token_present=", bool(n.token))
print("chat_id=", n.chat_id)
print("proxy=", n.proxy)

print("TRADE_SIGNAL_NOTIFIER_OK")
PY
