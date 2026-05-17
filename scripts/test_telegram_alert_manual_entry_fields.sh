#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile src/scripts/send_grafana_alerts_telegram.py

python - <<'PY'
from pathlib import Path

text = Path("src/scripts/send_grafana_alerts_telegram.py").read_text(encoding="utf-8")

checks = [
    "Ручной сценарий",
    "Стоп-лосс",
    "Тейк-профит",
    "Количество",
    "Вероятность профита",
    "Не автосделка",
    "probability_pct",
]

for c in checks:
    assert c in text, c

print("OK: telegram alert manual entry fields")
PY
