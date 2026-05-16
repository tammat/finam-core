#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile src/scripts/update_market_opportunity_metrics.py

python - <<'PY'
from pathlib import Path

text = Path("src/scripts/update_market_opportunity_metrics.py").read_text(encoding="utf-8")

assert "smart_money_score" in text
assert "smart_money_label" in text
assert "smart_money_feature_events" in text
assert "NO_SMART_MONEY_DATA" in text

print("OK: market opportunity updater includes smart money features")
PY
