#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile src/finam_core/notifications/manual_position_pnl_formatter.py

python - <<'PY'
from finam_core.notifications.manual_position_pnl_formatter import (
    ManualPositionPnlAlert,
    format_manual_position_pnl_alert,
)

alert = ManualPositionPnlAlert(
    symbol="T",
    qty=50,
    average_price=324.25,
    current_price=318.52,
    price_delta=-5.73,
    pnl_pct=-1.77,
    status="LOSS",
    recommendation="контролировать уровень стопа, не усреднять без нового сигнала",
)

text = format_manual_position_pnl_alert(alert)

assert "Ручная позиция Finam" in text
assert "Инструмент: T" in text
assert "PnL: -1.77%" in text
assert "Рекомендация" in text

print(text)
print("OK")
PY
