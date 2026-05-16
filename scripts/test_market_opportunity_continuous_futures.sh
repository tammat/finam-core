#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile src/scripts/update_market_opportunity_metrics.py

python - <<'PY'
from pathlib import Path

text = Path("src/scripts/update_market_opportunity_metrics.py").read_text(encoding="utf-8")

checks = [
    "FUTURES_CONTINUOUS",
    "BR_CONT",
    "NG_CONT",
    "USDRUB_CONT",
    "continuous_smart_money_context",
    "smart_money_feature_events",
]

for c in checks:
    assert c in text, c

print("OK: market opportunity updater includes continuous futures context")
PY
