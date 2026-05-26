#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile \
  src/scripts/build_trade_outcomes.py \
  src/finam_core/analytics/regime_attribution.py \
  src/finam_core/analytics/trade_outcome_engine.py

python - <<'PY'
import importlib.util

spec = importlib.util.spec_from_file_location(
    "build_trade_outcomes",
    "src/scripts/build_trade_outcomes.py",
)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

payload = {
    "payload": {
        "regime": "trend_up_high_vol",
        "regime_label": "trend_up_high_vol",
        "reason": "BR_M5_BREAKOUT_UP_trend_high_vol_HIGH_VOL_TREND_PRESET",
        "continuous_symbol": "BR_CONT",
        "strategy": "BR_CONSERVATIVE_BREAKOUT",
    }
}

enriched = mod._enrich_regime_payload(payload)

assert enriched["regime"] == "trend_up_high_vol"
assert enriched["regime_label"] == "trend_up_high_vol"
assert enriched["continuous_symbol"] == "BR_CONT"
assert enriched["strategy"] == "BR_CONSERVATIVE_BREAKOUT"
assert enriched["_nested_payload_unwrapped"] is True

print("TRADE_OUTCOME_ENGINE_V1_2_PAYLOAD_UNWRAP_UNIT_OK")
PY

echo "TRADE_OUTCOME_ENGINE_V1_2_COMPILE_OK"
