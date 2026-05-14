#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python - <<'PY'
from finam_core.strategy.equities.mean_reversion_equity import MeanReversionEquity

s = MeanReversionEquity()

symbol = "LKOH@MISX"

# Русский комментарий:
# сначала нормальная история.

for i in range(30):

    state = {
        "symbol": symbol,
        "last": 5000.0,
        "volume": 1000,
        "atr": 25.0,
    }

    s.on_quote(state)

# Русский комментарий:
# теперь сильное отклонение вниз.

signal = s.on_quote({
    "symbol": symbol,
    "last": 4800.0,
    "volume": 5000,
    "atr": 40.0,
})

assert signal is not None, "signal is None"

print(signal)
print("OK: MeanReversionEquity")
PY
