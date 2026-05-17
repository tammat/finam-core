#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile src/scripts/adaptive_regime_decision_analytics.py

python - <<'PY'
from pathlib import Path

text = Path("src/scripts/adaptive_regime_decision_analytics.py").read_text(encoding="utf-8")

checks = [
    "Решение adaptive regime",
    "Режим крупного капитала",
    "Средний множитель режима",
    "adaptive_regime_action",
    "adaptive_regime_multiplier",
    "adaptive_regime_decision_analytics.tsv",
]

for c in checks:
    assert c in text, c

print("OK: adaptive regime decision analytics static check")
PY

PYTHONPATH=src python src/scripts/adaptive_regime_decision_analytics.py

test -f reports/strategy_analytics/adaptive_regime_decision_analytics.tsv

echo "OK: adaptive regime decision analytics"
