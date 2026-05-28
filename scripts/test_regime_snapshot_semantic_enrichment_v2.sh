#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH="${PYTHONPATH:-src}"

python -m py_compile src/scripts/analytics/build_regime_snapshots_v2.py

python - <<'PY'
from scripts.analytics.build_regime_snapshots_v2 import classify

r = classify({
    "volatility_state": "low",
    "trend_state": "flat",
    "range_state": "narrow",
    "atr_proxy": "0.12",
    "quality": "FULL",
})
assert r[0] == "compression", r
assert r[1] == "low", r
assert r[2] == "flat", r
assert r[3] == "compression", r
assert r[4] > 0.7, r

r = classify({
    "volatility_state": "high",
    "trend_state": "up",
    "range_state": "wide",
    "atr_proxy": "1.5",
    "quality": "FULL",
})
assert r[0] == "trend_up_expansion", r
assert r[3] == "expansion", r

r = classify({
    "volatility_state": "normal",
    "trend_state": "down",
    "range_state": "wide",
    "quality": "PARTIAL",
})
assert r[0] == "trend_down", r
assert r[3] == "normal", r

print("REGIME_SNAPSHOT_SEMANTIC_ENRICHMENT_UNIT_OK")
PY

grep -q "volatility_state" src/scripts/analytics/build_regime_snapshots_v2.py
grep -q "trend_state" src/scripts/analytics/build_regime_snapshots_v2.py
grep -q "compression" src/scripts/analytics/build_regime_snapshots_v2.py

echo "REGIME_SNAPSHOT_SEMANTIC_ENRICHMENT_V2_TEST_OK"
