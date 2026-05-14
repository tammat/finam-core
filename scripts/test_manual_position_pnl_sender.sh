#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile \
  src/finam_core/notifications/manual_position_pnl_sender.py \
  src/finam_core/notifications/manual_position_pnl_formatter.py \
  src/finam_core/reconciliation/manual_position_pnl_analyzer.py

python - <<'PY'
from finam_core.reconciliation.manual_position_pnl_analyzer import analyze_position
from finam_core.notifications.manual_position_pnl_sender import send_manual_position_pnl_alert

class FakeNotifier:
    def __init__(self):
        self.messages = []

    def send(self, text):
        self.messages.append(text)

n = FakeNotifier()

loss = analyze_position(symbol="T", qty=50, average_price=324.25, current_price=318.52)
assert loss is not None
assert send_manual_position_pnl_alert(n, loss) is True

profit = analyze_position(symbol="SGZH", qty=10000, average_price=0.8795, current_price=0.897)
assert profit is not None
assert send_manual_position_pnl_alert(n, profit) is True

flat = analyze_position(symbol="TEST", qty=1, average_price=100, current_price=100.03)
assert flat is not None
assert send_manual_position_pnl_alert(n, flat) is False

assert len(n.messages) == 2
assert "Ручная позиция Finam" in n.messages[0]
assert "Рекомендация" in n.messages[0]

print("OK: manual position PnL sender works")
PY
