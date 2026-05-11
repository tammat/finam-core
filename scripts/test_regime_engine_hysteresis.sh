#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core

grep -q "REGIME_CONFIRM_TICKS" src/finam_core/regime/regime_engine.py
grep -q "_confirmed_regime_key" src/finam_core/regime/regime_engine.py
grep -q "_candidate_regime_key" src/finam_core/regime/regime_engine.py
grep -q "_candidate_regime_count" src/finam_core/regime/regime_engine.py
grep -q "raw_regime_key" src/finam_core/regime/regime_engine.py

REGIME_CONFIRM_TICKS=3 PYTHONPATH=src python - <<'PY'
from finam_core.regime.regime_engine import RegimeEngine

engine = RegimeEngine(window=5)

engine.evaluate(100.00, {"atr": 0.03})
d2 = engine.evaluate(100.00, {"atr": 0.03})
assert d2.regime_type == "dead", d2.regime_type
assert d2.trend == "flat", d2.trend

# До накопления окна len(prices) >= 5 режим не должен прыгать.
d3 = engine.evaluate(100.10, {"atr": 0.03})
assert d3.regime_type == "dead", d3.regime_type

d4 = engine.evaluate(100.20, {"atr": 0.03})
assert d4.regime_type == "dead", d4.regime_type

# С этого момента raw trend уже up, но нужен REGIME_CONFIRM_TICKS=3.
d5 = engine.evaluate(100.30, {"atr": 0.03})
assert d5.regime_type == "dead", d5.regime_type

d6 = engine.evaluate(100.40, {"atr": 0.03})
assert d6.regime_type == "dead", d6.regime_type

d7 = engine.evaluate(100.50, {"atr": 0.03})
assert d7.regime_type == "trend", d7.regime_type
assert d7.trend == "up", d7.trend

print("REGIME_ENGINE_HYSTERESIS_RUNTIME_OK")
PY

python -m py_compile src/finam_core/regime/regime_engine.py

echo "REGIME_ENGINE_HYSTERESIS_TEST_OK"
