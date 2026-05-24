#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile \
  src/finam_core/runtime/intermarket_selection_modifier.py \
  src/scripts/runtime/apply_intermarket_selection_modifier.py

python - <<'PY'
from finam_core.runtime.intermarket_selection_modifier import build_intermarket_modifier

boost = build_intermarket_modifier(
    strategy="NG_CONSERVATIVE_BREAKOUT",
    root_symbol="NG",
    risk_mode="RISK_ON_COMMODITY",
    commodity_mode="COMMODITY_EXPANSION",
    confidence=0.5,
    commodity_score=0.4,
    fx_stress_score=0.0,
)
assert boost.score_multiplier > 1.0
assert boost.recommendation_suffix == "IM_COMMODITY_BOOST"

reduce = build_intermarket_modifier(
    strategy="NG_CONSERVATIVE_BREAKOUT",
    root_symbol="NG",
    risk_mode="RISK_OFF",
    commodity_mode="LOW_IMPULSE",
    confidence=0.5,
    commodity_score=0.0,
    fx_stress_score=0.5,
)
assert reduce.score_multiplier < 1.0

neutral = build_intermarket_modifier(
    strategy="USD_INTRADAY_REGIME",
    root_symbol="USDRUB",
    risk_mode="NEUTRAL",
    commodity_mode="LOW_IMPULSE",
    confidence=0.1,
    commodity_score=0.0,
    fx_stress_score=0.0,
)
assert neutral.score_multiplier == 1.0

print("INTERMARKET_SELECTION_MODIFIER_UNIT_OK")
PY

grep -q "runtime_strategy_scores_latest" src/scripts/runtime/apply_intermarket_selection_modifier.py
grep -q "intermarket_regime_snapshots" src/scripts/runtime/apply_intermarket_selection_modifier.py
grep -q "INTERMARKET_SELECTION_MODIFIER_OK" src/scripts/runtime/apply_intermarket_selection_modifier.py

echo "INTERMARKET_SELECTION_MODIFIER_V1_TEST_OK"
