#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile \
  src/finam_core/alpha/regime_layer_v2.py \
  src/scripts/run_regime_layer_v2.py

python - <<'PY'
from finam_core.alpha.regime_layer_v2 import RegimeLayerV2

layer = RegimeLayerV2(min_points=25)

up_prices = [100 + i * 0.2 for i in range(30)]
d = layer.classify(symbol="SBER@MISX", prices=up_prices)
assert d.regime == "trend_up", d
assert d.tradable is True

flat_prices = [100.0 for _ in range(30)]
d2 = layer.classify(symbol="SBER@MISX", prices=flat_prices)
assert d2.regime == "compression", d2
assert d2.tradable is False

print("OK: regime layer v2")
PY

grep -q "regime_state" src/scripts/run_regime_layer_v2.py
grep -q "REGIME_LAYER_V2_STATE" src/scripts/run_regime_layer_v2.py

echo "OK: regime layer v2 script"
