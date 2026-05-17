#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile src/scripts/commission_aware_strategy_analytics.py

python - <<'PY'
from pathlib import Path

text = Path("src/scripts/commission_aware_strategy_analytics.py").read_text(encoding="utf-8")

checks = [
    "ANALYTICS_COMMISSION_BPS",
    "ANALYTICS_SLIPPAGE_BPS",
    "Комиссии",
    "Оценочное проскальзывание",
    "Итого издержки",
    "Издержки на сделку",
    "Издержки, % оборота",
    "commission_aware_strategy_analytics.tsv",
]

for c in checks:
    assert c in text, c

print("OK: commission-aware strategy analytics static check")
PY

PYTHONPATH=src python src/scripts/commission_aware_strategy_analytics.py

test -f reports/strategy_analytics/commission_aware_strategy_analytics.tsv

echo "OK: commission-aware strategy analytics"
