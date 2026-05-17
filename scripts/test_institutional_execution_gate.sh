#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile src/finam_core/risk/institutional_execution_gate.py

python - <<'PY'
from datetime import datetime

from finam_core.risk.institutional_execution_gate import InstitutionalExecutionGate

gate = InstitutionalExecutionGate()

d1 = gate.evaluate(
    symbol="BRM6@RTSX",
    strategy="BR_CONSERVATIVE_BREAKOUT",
    regime_ru="🚀 Запуск тренда",
    has_inventory_event_today=True,
    minutes_to_event=20,
    now=datetime(2026, 5, 17, 12, 0),
)
assert d1.allowed is False
assert d1.action == "BLOCK"
assert "запас" in d1.reason

d2 = gate.evaluate(
    symbol="USDRUBF@RTSX",
    strategy="USDRUB_REGIME",
    regime_ru="⚪ Обычная активность",
    has_cbr_event_today=True,
    now=datetime(2026, 5, 17, 12, 0),
)
assert d2.allowed is True
assert d2.action == "REDUCE"
assert d2.multiplier == 0.5
assert "ЦБ" in d2.reason

d3 = gate.evaluate(
    symbol="SBER@MISX",
    strategy="TREND_PULLBACK_EQUITY",
    regime_ru="🟢 Накопление",
    churn_status="🟢 Нормальная частота",
    now=datetime(2026, 5, 17, 12, 0),
)
assert d3.allowed is True
assert d3.action == "ALLOW"

d4 = gate.evaluate(
    symbol="NGK6@RTSX",
    strategy="NG_SCALP",
    regime_ru="⚪ Обычная активность",
    churn_status="🔴 Критический churn",
    now=datetime(2026, 5, 17, 12, 0),
)
assert d4.allowed is False
assert d4.action == "BLOCK"

print("OK: InstitutionalExecutionGate")
PY
