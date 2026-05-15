#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile src/finam_core/regime/regime_labeler.py

python - <<'PY'
from finam_core.regime.regime_labeler import RegimeLabeler

assert RegimeLabeler.label({"trend": "bullish", "volatility": "high"}) == "trend_up_high_vol"
assert RegimeLabeler.label({"trend": "bearish", "volatility": "low"}) == "trend_down_low_vol"
assert RegimeLabeler.label({"trend": "range", "atr_pct": 0.003}) == "range_low_vol"
assert RegimeLabeler.label({"compression": True}) == "compression"
assert RegimeLabeler.label({"breakout": True}) == "breakout"
assert RegimeLabeler.label({}) == "unknown_trend_unknown_vol"

print("OK: RegimeLabeler works")
PY
