#!/usr/bin/env bash
set -euo pipefail

PYTHONPATH=src python - <<'PY'
from finam_core.risk.live_atr import LiveAtrEstimator

atr = LiveAtrEstimator(window=3, default_atr=0.1)

assert atr.value() == 0.1
assert atr.update(100.0) == 0.1

v1 = atr.update(100.2)
assert round(v1, 6) == 0.2

v2 = atr.update(99.9)
assert round(v2, 6) == 0.25

v3 = atr.update(100.5)
assert round(v3, 6) == round((0.2 + 0.3 + 0.6) / 3, 6)

print("OK live_atr")
PY
