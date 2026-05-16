#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile src/finam_core/orderflow/smart_money_features.py

python - <<'PY'
from finam_core.orderflow.smart_money_features import SmartMoneyFeatureLayer

layer = SmartMoneyFeatureLayer(window=5)

normal = layer.update(
    symbol="SBER@MISX",
    price=300,
    volume=1000,
    high=301,
    low=299,
    avg_volume=1000,
)

assert normal.label in {"NORMAL_FLOW", "SMART_MONEY_CANDIDATE"}

absorb = layer.update(
    symbol="SBER@MISX",
    price=300.1,
    volume=6000,
    high=300.3,
    low=299.9,
    avg_volume=1000,
)

assert absorb.rvol >= 6.0
assert absorb.absorption_score > 0.0
assert absorb.smart_money_score > normal.smart_money_score

impulse = layer.update(
    symbol="SBER@MISX",
    price=306,
    volume=5000,
    high=307,
    low=300,
    avg_volume=1000,
)

assert impulse.impulse_score > 0.0
assert impulse.smart_money_score > 0.0

print("OK: SmartMoneyFeatureLayer")
PY
