#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH="${PYTHONPATH:-src}"

python -m py_compile \
  src/finam_core/analytics/trade_context_envelope.py \
  src/finam_core/analytics/context_quality_engine.py \
  src/scripts/analytics/build_trade_context_envelopes.py

python - <<'PY'
from finam_core.analytics.context_quality_engine import ContextQualityEngine

engine = ContextQualityEngine()

full = engine.evaluate({
    "strategy": "BR",
    "timeframe": "M5",
    "risk": {"heat_status": "LOW"},
    "strategy_context": {"exit_policy": {"type": "trailing"}},
    "feature_snapshot": {"atr": 1.0},
})
assert full.quality == "FULL", full

partial = engine.evaluate({
    "strategy": "BR",
    "timeframe": "M5",
    "risk": {},
    "strategy_context": {},
    "feature_snapshot": {"atr": 1.0},
})
assert partial.quality in {"PARTIAL", "WEAK"}, partial

print("CONTEXT_QUALITY_ENGINE_UNIT_OK")
PY

grep -q "trade_context_envelopes" src/scripts/analytics/build_trade_context_envelopes.py
grep -q "v_trade_context_envelopes_ru" src/scripts/analytics/build_trade_context_envelopes.py
grep -q "v_trade_context_quality_summary_ru" src/scripts/analytics/build_trade_context_envelopes.py

echo "TRADE_CONTEXT_ENVELOPE_V1_TEST_OK"
