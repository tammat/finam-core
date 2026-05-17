#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile src/scripts/turnover_churn_analytics.py

python - <<'PY'
from pathlib import Path

text = Path("src/scripts/turnover_churn_analytics.py").read_text(encoding="utf-8")

checks = [
    "Сделок на 1000 ₽ оборота",
    "Критический churn",
    "Высокий churn",
    "Средний churn",
    "Нормальная частота",
    "turnover_churn_analytics.tsv",
]

for c in checks:
    assert c in text, c

print("OK: turnover churn analytics static check")
PY

PYTHONPATH=src python src/scripts/turnover_churn_analytics.py

test -f reports/strategy_analytics/turnover_churn_analytics.tsv

echo "OK: turnover churn analytics"
