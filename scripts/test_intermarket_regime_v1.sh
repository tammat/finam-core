#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile \
  src/finam_core/research/intermarket_regime.py \
  src/scripts/research/build_intermarket_regime_snapshot.py

python - <<'PY'
from finam_core.research.intermarket_regime import IntermarketInput, classify_intermarket_regime

risk_off = classify_intermarket_regime(
    IntermarketInput(
        br_score=-0.2,
        ng_score=-0.1,
        gold_score=0.5,
        silver_score=0.2,
        usdrub_score=0.6,
        cny_score=0.4,
    )
)
assert risk_off.risk_mode == "RISK_OFF"

commodity = classify_intermarket_regime(
    IntermarketInput(
        br_score=0.5,
        ng_score=0.4,
        gold_score=0.3,
        silver_score=0.2,
        usdrub_score=0.0,
        cny_score=0.0,
    )
)
assert commodity.commodity_mode == "COMMODITY_EXPANSION"

neutral = classify_intermarket_regime(IntermarketInput())
assert neutral.risk_mode == "NEUTRAL"

print("INTERMARKET_REGIME_V1_UNIT_OK")
PY

echo "INTERMARKET_REGIME_V1_TEST_OK"
