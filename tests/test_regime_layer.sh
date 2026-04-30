#!/usr/bin/env bash
set -euo pipefail

PYTHONPATH=src REGIME_MIN_ATR=0.03 REGIME_MAX_ATR=0.8 REGIME_MIN_SLOPE=0.0 python - <<'PY'
self.regime_layer = RegimeLayer()from finam_core.risk.regime_layer import RegimeLayer

r = RegimeLayer()

assert r.evaluate(0.01, 100).allowed is False
assert r.evaluate(1.00, 100).allowed is False

r2 = RegimeLayer()
r2.evaluate(0.10, 100)
d = r2.evaluate(0.10, 101)
assert d.allowed is True
assert d.regime == "trend_up"

r3 = RegimeLayer()
r3.evaluate(0.10, 101)
d = r3.evaluate(0.10, 100)
assert d.allowed is True
assert d.regime == "trend_down"

print("OK regime_layer")
PY
