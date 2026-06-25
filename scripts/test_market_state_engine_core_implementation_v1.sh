#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core || exit 1

echo "=== TEST_MARKET_STATE_ENGINE_CORE_IMPLEMENTATION_V1 ==="

python3 -m py_compile \
  src/finam_core/research/market_state/__init__.py \
  src/finam_core/research/market_state/types.py \
  src/finam_core/research/market_state/result.py \
  src/finam_core/research/market_state/feature_validator.py \
  src/finam_core/research/market_state/feature_normalizer.py \
  src/finam_core/research/market_state/classifier_pipeline.py \
  src/finam_core/research/market_state/conflict_resolver.py \
  src/finam_core/research/market_state/quality_evaluator.py \
  src/finam_core/research/market_state/signature_builder.py \
  src/finam_core/research/market_state/explanation_builder.py \
  src/finam_core/research/market_state/engine.py

PYTHONPATH=src python3 - <<'PY'
from finam_core.research.market_state import MarketStateEngine

engine = MarketStateEngine()

features = {
    "symbol": "SBER@MISX",
    "timeframe": "M5",
    "close": 300.0,
    "trend": "UP",
    "volatility": "HIGH",
    "session": "MOSCOW_DAY",
}

first = engine.build(features)
second = engine.build(features)

assert first.canonical_signature == second.canonical_signature
assert first.compact_signature == second.compact_signature
assert first.orders_sent == 0
assert first.buy_sell_hold_decision == "NONE"
assert first.quality == "GOOD"
assert first.confidence > 0
assert first.conflict_score == 0
assert "TREND=UP" in first.canonical_signature
assert "VOLATILITY=HIGH" in first.canonical_signature
assert "SESSION_BUCKET=MOSCOW_DAY" in first.canonical_signature
assert len(first.events) >= 6
assert any(event.event_type == "MarketStateBuiltEvent" for event in first.events)
assert first.explanation_tree_ru

invalid = engine.build({"symbol": "SBER@MISX"})
assert invalid.quality == "INVALID_FEATURE_SET"
assert invalid.orders_sent == 0
assert invalid.buy_sell_hold_decision == "NONE"

print("RESULT canonical_signature=" + first.canonical_signature)
print("RESULT compact_signature=" + first.compact_signature)
print("RESULT quality=" + first.quality)
print("RESULT confidence=" + str(first.confidence))
print("RESULT conflict_score=" + str(first.conflict_score))
print("RESULT events=" + str(len(first.events)))
print("RESULT invalid_quality=" + invalid.quality)
print("orders_sent=0")
print("runtime_changed=0")
print("execution_changed=0")
print("real_trading_enabled=0")
print("VERDICT=MARKET_STATE_ENGINE_CORE_IMPLEMENTATION_OK")
PY

if grep -R "from .*execution\|import .*execution\|OrderClient\|broker_adapter\|real_trading_enabled *= *1" \
  src/finam_core/research/market_state; then
  echo "FORBIDDEN_IMPORT_OR_REAL_TRADING_FLAG_FOUND"
  exit 1
fi

echo "TEST_MARKET_STATE_ENGINE_CORE_IMPLEMENTATION_V1_OK"
