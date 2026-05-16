#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile \
  src/finam_core/orderflow/continuous_smart_money_aggregator.py \
  src/scripts/aggregate_continuous_smart_money.py

python - <<'PY'
from pathlib import Path

text = Path("src/finam_core/orderflow/continuous_smart_money_aggregator.py").read_text(encoding="utf-8")

checks = [
    "BR_CONT",
    "BRM6@RTSX",
    "BRN6@RTSX",
    "smart_money_feature_events",
    "ContinuousSmartMoneyAggregator",
]

for c in checks:
    assert c in text, c

print("OK: ContinuousSmartMoneyAggregator static check")
PY
