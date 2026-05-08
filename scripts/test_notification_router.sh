#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python - <<'PY'
from finam_core.notifications.notification_router import NotificationRouter

sent = []

class FakeSystem:
    def send(self, text):
        sent.append(("system", text))

class FakeTrade:
    def send_text(self, text):
        sent.append(("trade", text))
        return True

r = NotificationRouter()
r.system_notifier = FakeSystem()
r.trade_notifier = FakeTrade()

assert r.send(trigger="market_radar", text="radar") is True
assert r.send(trigger="trade_signal", text="signal") is True
assert sent == [("system", "radar"), ("trade", "signal")], sent

print("NOTIFICATION_ROUTER_OK")
PY
