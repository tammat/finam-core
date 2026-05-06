#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python - <<'PY'
from finam_core.strategy.br_regime_layer import BRRegimeLayer

r = BRRegimeLayer()

d = r.evaluate(
    atr_pct=0.01,
    slope_m5=0.001,
    slope_m15=0.001,
    compression_ratio=0.9,
    signal_side="BUY",
)
assert d.allowed is True
assert d.regime == "trend_expansion_up"

d = r.evaluate(
    atr_pct=0.0005,
    slope_m5=0.001,
    slope_m15=0.001,
    compression_ratio=0.9,
    signal_side="BUY",
)
assert d.allowed is False
assert d.regime == "dead_market"

d = r.evaluate(
    atr_pct=0.01,
    slope_m5=0.001,
    slope_m15=0.001,
    compression_ratio=0.9,
    signal_side="SELL",
)
assert d.allowed is False
assert d.regime == "misaligned"

d = r.evaluate(
    atr_pct=0.01,
    slope_m5=0.001,
    slope_m15=0.001,
    compression_ratio=0.4,
    signal_side="BUY",
)
assert d.allowed is False
assert d.regime == "compression"

print("BR_REGIME_LAYER_OK")
PY
