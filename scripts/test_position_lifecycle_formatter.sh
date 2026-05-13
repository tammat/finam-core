#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python - <<'PY'
from finam_core.notifications.position_lifecycle_formatter import (
    PositionLifecycleAlert,
    format_position_lifecycle_alert,
)

alert = PositionLifecycleAlert(
    event_type="PIPE_BREAK_EVEN",
    symbol="BRM6@RTSX",
    side="BUY",
    horizon="INTRADAY",
    old_stop=106.90,
    new_stop=107.55,
    current_price=108.10,
    reason="цена прошла +1R",
)

text = format_position_lifecycle_alert(alert)

assert "Сопровождение позиции" in text
assert "Стоп перенесён в безубыток" in text
assert "Старый SL" in text
assert "Новый SL" in text
assert "Текущая цена" in text

print(text)
print("OK")
PY
