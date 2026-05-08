#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python - <<'PY'
from finam_core.notifications.trade_signal_notifier import TradeSignalNotifier

n = TradeSignalNotifier()
assert hasattr(n, "send_text")

print("TRADE_SIGNAL_NOTIFIER_SEND_TEXT_OK")
PY
