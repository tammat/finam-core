#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core || exit 1

echo "=== TEST_MARKET_STATE_ENGINE_EVENT_ADAPTER_IMPLEMENTATION_V1 ==="

python3 -m py_compile \
  src/finam_core/research/events.py \
  src/finam_core/research/event_adapter.py

PYTHONPATH=src python3 - <<'PY'
from finam_core.research.event_adapter import ResearchEventAdapter
from finam_core.research.events import MarketFeaturesReadyEvent, MarketStateBuiltEvent

adapter = ResearchEventAdapter()

event = MarketFeaturesReadyEvent(
    symbol="SBER@MISX",
    timeframe="M5",
    features={
        "close": 300.0,
        "trend": "UP",
        "volatility": "HIGH",
        "session": "MOSCOW_DAY",
    },
)

result = adapter.handle_market_features(event)

assert isinstance(result, MarketStateBuiltEvent)
assert result.symbol == "SBER@MISX"
assert result.timeframe == "M5"
assert result.quality == "GOOD"
assert result.confidence > 0
assert "TREND=UP" in result.canonical_signature
assert "VOLATILITY=HIGH" in result.canonical_signature
assert result.payload["orders_sent"] == 0
assert result.payload["buy_sell_hold_decision"] == "NONE"
assert result.payload["engine_events"]

dict_result = adapter.handle_market_features({
    "symbol": "BRN6@RTSX",
    "timeframe": "M5",
    "features": {
        "close": 80.0,
        "trend": "DOWN",
        "volatility": "NORMAL",
        "session": "MOSCOW_DAY",
    },
})

assert dict_result.symbol == "BRN6@RTSX"
assert "TREND=DOWN" in dict_result.canonical_signature
assert dict_result.payload["orders_sent"] == 0

print("RESULT event=MarketStateBuiltEvent")
print("RESULT symbol=" + result.symbol)
print("RESULT canonical_signature=" + result.canonical_signature)
print("RESULT compact_signature=" + result.compact_signature)
print("RESULT quality=" + result.quality)
print("orders_sent=0")
print("runtime_changed=0")
print("execution_changed=0")
print("real_trading_enabled=0")
print("VERDICT=MARKET_STATE_ENGINE_EVENT_ADAPTER_IMPLEMENTATION_OK")
PY

if grep -R "from .*execution\|import .*execution\|OrderClient\|broker_adapter\|real_trading_enabled *= *1" \
  src/finam_core/research/event_adapter.py src/finam_core/research/events.py; then
  echo "FORBIDDEN_IMPORT_OR_REAL_TRADING_FLAG_FOUND"
  exit 1
fi

echo "TEST_MARKET_STATE_ENGINE_EVENT_ADAPTER_IMPLEMENTATION_V1_OK"
