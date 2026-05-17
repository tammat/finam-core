#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile src/scripts/send_grafana_alerts_telegram.py

python - <<'PY'
from pathlib import Path

text = Path("src/scripts/send_grafana_alerts_telegram.py").read_text(encoding="utf-8")

checks = [
    "format_reason_ru",
    "Выбранный фьючерс для исполнения",
    "Причина: выбран наиболее ликвидный/активный контракт",
    "🎯 <b>Момент точки входа</b>",
    "📌 Условная заявка на вход",
    "🛑 Стоп-лосс",
    "💰 Тейк-профит",
    "⚖️ Количество",
]

for c in checks:
    assert c in text, c

print("OK: telegram alert RU formatter")
PY
