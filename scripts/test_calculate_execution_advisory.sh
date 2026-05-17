#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile \
  src/scripts/calculate_execution_advisory.py

python - <<'PY'
from pathlib import Path

text = Path("src/scripts/calculate_execution_advisory.py").read_text(encoding="utf-8")

checks = [
    "Условная заявка на вход",
    "Стоп-лосс",
    "Тейк-профит",
    "Вероятность профита %",
    "calculate_levels",
    "institutional_flow_regime_events",
]

for c in checks:
    assert c in text, c

print("OK: execution advisory static check")
PY

PYTHONPATH=src python src/scripts/calculate_execution_advisory.py

test -f reports/execution_advisory.tsv

echo "OK: execution advisory report"
