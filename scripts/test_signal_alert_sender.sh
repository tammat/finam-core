#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python - <<'PY'
from dataclasses import dataclass
from finam_core.notifications.signal_alert_sender import send_signal_alert_from_intent

class FakeNotifier:
    def __init__(self):
        self.text = None

    def send(self, text):
        self.text = text

@dataclass
class FakeIntent:
    symbol: str = "BRM6@RTSX"
    side: str = "BUY"
    entry_price: float = 107.55
    stop_loss: float = 106.90
    take_profit: float = 108.85
    timeframe: str = "M5"
    reason: str = "тестовая торговая точка"
    confidence: float = 0.74
    risk_rub: float = 650.0

notifier = FakeNotifier()
send_signal_alert_from_intent(notifier, FakeIntent())

assert notifier.text is not None
assert "Торговая точка" in notifier.text
assert "Вход:" in notifier.text
assert "Стоп-лосс:" in notifier.text
assert "Тейк-профит:" in notifier.text
assert "Заявка не выставлена" in notifier.text
assert "order_id" not in notifier.text.lower()
assert "fill" not in notifier.text.lower()
assert "сделка" not in notifier.text.lower()

print(notifier.text)
print("OK")
PY
