#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core || exit 1

echo "=== TEST_MARKET_STATE_ENGINE_RUNTIME_SHADOW_IMPLEMENTATION_V1 ==="

python3 -m py_compile \
  src/finam_core/research/runtime_shadow_subscriber.py \
  src/finam_core/research/runtime_shadow_pipeline.py

PYTHONPATH=src python3 - <<'PY'
from finam_core.research.runtime_shadow_pipeline import RuntimeShadowPipeline

pipeline = RuntimeShadowPipeline()

event = {
    "symbol": "SBER@MISX",
    "timeframe": "M5",
    "close": 300.0,
    "trend": "UP",
    "volatility": "HIGH",
    "session": "MOSCOW_DAY",
}

result = pipeline.process_market_event(event)

assert result["symbol"] == "SBER@MISX"
assert result["timeframe"] == "M5"
assert result["event_type"] == "MarketStateBuiltEvent"
assert "TREND=UP" in result["canonical_signature"]
assert "VOLATILITY=HIGH" in result["canonical_signature"]
assert result["compact_signature"].startswith("MS-")
assert result["quality"] == "GOOD"
assert result["orders_sent"] == 0
assert result["buy_sell_hold_decision"] == "NONE"

second = pipeline.process_market_event(event)

assert second["canonical_signature"] == result["canonical_signature"]
assert second["compact_signature"] == result["compact_signature"]

print("RESULT symbol=" + result["symbol"])
print("RESULT timeframe=" + result["timeframe"])
print("RESULT canonical_signature=" + result["canonical_signature"])
print("RESULT compact_signature=" + result["compact_signature"])
print("RESULT quality=" + result["quality"])
print("orders_sent=0")
print("runtime_changed=0")
print("execution_changed=0")
print("real_trading_enabled=0")
print("VERDICT=MARKET_STATE_ENGINE_RUNTIME_SHADOW_IMPLEMENTATION_OK")
PY

if grep -R "from .*execution\|import .*execution\|OrderClient\|broker_adapter\|real_trading_enabled *= *1" \
  src/finam_core/research/runtime_shadow_subscriber.py \
  src/finam_core/research/runtime_shadow_pipeline.py; then
  echo "FORBIDDEN_IMPORT_OR_REAL_TRADING_FLAG_FOUND"
  exit 1
fi

echo "TEST_MARKET_STATE_ENGINE_RUNTIME_SHADOW_IMPLEMENTATION_V1_OK"
