#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH="${PYTHONPATH:-src}"

python -m py_compile \
  src/finam_core/research/ng_regime_v2.py \
  src/scripts/build_ng_regime_v2_analytics.py

python - <<'PY'
from finam_core.research.ng_regime_v2 import NgRegimeFeaturesV2, classify_ng_regime_v2

r = classify_ng_regime_v2(NgRegimeFeaturesV2(
    atr_percent=1.5,
    atr_expansion=1.4,
    range_expansion=1.5,
    ema_slope=0.12,
    compression_score=0.2,
    breakout_strength=1.8,
    session_bucket="US_OPEN_WINDOW",
))
assert r == "EXPANSION_TREND_UP"

r2 = classify_ng_regime_v2(NgRegimeFeaturesV2(
    atr_percent=0.8,
    atr_expansion=1.0,
    range_expansion=1.4,
    ema_slope=0.0,
    compression_score=0.8,
    breakout_strength=1.0,
    session_bucket="MOEX_DAY",
))
assert r2 == "SQUEEZE_BREAKOUT"

print("TEST_NG_REGIME_V2_OK")
PY
