#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile src/scripts/pnl_by_institutional_regime.py

python - <<'PY'
from pathlib import Path

text = Path("src/scripts/pnl_by_institutional_regime.py").read_text(encoding="utf-8")

checks = [
    "🟢 Накопление",
    "🔴 Распределение",
    "🚀 Запуск тренда",
    "🪤 Ловушка пробоя",
    "Чистая прибыль после издержек и налога",
    "Средняя чистая прибыль на сделку",
    "pnl_by_institutional_regime.tsv",
]

for c in checks:
    assert c in text, c

print("OK: PnL by institutional regime static check")
PY

PYTHONPATH=src python src/scripts/pnl_by_institutional_regime.py

test -f reports/strategy_analytics/pnl_by_institutional_regime.tsv

echo "OK: PnL by institutional regime"
