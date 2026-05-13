#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python - <<'PY'
from finam_core.notifications.signal_alert_formatter import SignalAlert, format_signal_alert

alert = SignalAlert(
    symbol="BRM6@RTSX",
    side="BUY",
    entry_price=107.55,
    stop_loss=106.90,
    take_profit=108.85,
    timeframe="M5",
    reason="пробой уровня и удержание цены выше входа",
    confidence=0.74,
    risk_rub=650.0,
)

text = format_signal_alert(alert)

assert "📍 Торговая точка" in text
assert "Вход:" in text
assert "Стоп-лосс:" in text
assert "Тейк-профит:" in text
assert "Заявка не выставлена" in text

for forbidden in ["order_id", "fill", "исполнено", "сделка"]:
    assert forbidden.lower() not in text.lower(), forbidden

print(text)
print("OK")
PY
