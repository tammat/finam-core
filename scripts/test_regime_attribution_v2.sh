#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile \
  src/finam_core/analytics/regime_attribution.py \
  src/finam_core/pipelines/paper_pipeline.py \
  src/scripts/build_trade_outcomes.py

python - <<'PY'
from finam_core.analytics.regime_attribution import derive_regime_label

assert derive_regime_label({"regime": "trend_up_high_vol"}) == "trend_up_high_vol"
assert derive_regime_label({"regime_direction": 1, "regime_atr_pct": 0.004}) == "trend_up_high_vol"
assert derive_regime_label({"regime_direction": -1, "regime_atr_pct": 0.004}) == "trend_down_high_vol"
assert derive_regime_label({"regime_direction": 0, "regime_atr_pct": 0.001}) == "flat_normal_vol"

print("REGIME_ATTRIBUTION_V2_UNIT_OK")
PY

grep -q "derive_regime_label" src/finam_core/pipelines/paper_pipeline.py
grep -q "_enrich_regime_payload" src/scripts/build_trade_outcomes.py

echo "REGIME_ATTRIBUTION_V2_COMPILE_OK"
