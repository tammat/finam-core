#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile src/scripts/realized_pnl_engine.py

python - <<'PY'
from pathlib import Path

text = Path("src/scripts/realized_pnl_engine.py").read_text(encoding="utf-8")

checks = [
    "Gross PnL",
    "Net PnL",
    "Налог",
    "Winrate %",
    "ANALYTICS_ESTIMATED_TAX_RATE",
    "PositionBook",
]

for c in checks:
    assert c in text, c

print("OK: realized pnl engine static check")
PY

PYTHONPATH=src python src/scripts/realized_pnl_engine.py

test -f reports/strategy_analytics/realized_pnl_engine.tsv

echo "OK: realized pnl engine"
