#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core || exit 1

echo "=== TEST_MARKET_STATE_ENGINE_EVENT_INTEGRATION_V1 ==="

python3 -m py_compile \
  src/finam_core/research/events.py \
  src/finam_core/research/event_adapter.py \
  src/finam_core/research/market_state/engine.py

PYTHONPATH=src python3 - <<'PY'
from finam_core.research.event_adapter import ResearchEventAdapter
from finam_core.research.events import MarketFeaturesReadyEvent, MarketStateBuiltEvent

adapter = ResearchEventAdapter()

events = [
    MarketFeaturesReadyEvent(
        symbol="SBER@MISX",
        timeframe="M5",
        features={
            "close": 300.0,
            "trend": "UP",
            "volatility": "HIGH",
            "session": "MOSCOW_DAY",
        },
    ),
    MarketFeaturesReadyEvent(
        symbol="BRN6@RTSX",
        timeframe="M5",
        features={
            "close": 80.0,
            "trend": "DOWN",
            "volatility": "NORMAL",
            "session": "MOSCOW_DAY",
        },
    ),
    MarketFeaturesReadyEvent(
        symbol="NGN6@RTSX",
        timeframe="M1",
        features={
            "close": 2.5,
            "trend": "UNKNOWN",
            "volatility": "HIGH",
            "session": "MOSCOW_EVENING",
        },
    ),
]

results = [adapter.handle_market_features(event) for event in events]

assert len(results) == 3

for result in results:
    assert isinstance(result, MarketStateBuiltEvent)
    assert result.symbol
    assert result.timeframe
    assert result.canonical_signature
    assert result.compact_signature.startswith("MS-")
    assert result.payload["orders_sent"] == 0
    assert result.payload["buy_sell_hold_decision"] == "NONE"
    assert result.payload["engine_events"]

first_again = adapter.handle_market_features(events[0])
assert first_again.canonical_signature == results[0].canonical_signature
assert first_again.compact_signature == results[0].compact_signature

qualities = ",".join(result.quality for result in results)

print("RESULT events_in=" + str(len(events)))
print("RESULT events_out=" + str(len(results)))
print("RESULT first_signature=" + results[0].canonical_signature)
print("RESULT first_compact=" + results[0].compact_signature)
print("RESULT qualities=" + qualities)
print("orders_sent=0")
print("runtime_changed=0")
print("execution_changed=0")
print("real_trading_enabled=0")
print("VERDICT=MARKET_STATE_ENGINE_EVENT_INTEGRATION_OK")
PY

if grep -R "from .*execution\|import .*execution\|OrderClient\|broker_adapter\|real_trading_enabled *= *1" \
  src/finam_core/research/event_adapter.py \
  src/finam_core/research/events.py \
  src/finam_core/research/market_state; then
  echo "FORBIDDEN_IMPORT_OR_REAL_TRADING_FLAG_FOUND"
  exit 1
fi

echo "TEST_MARKET_STATE_ENGINE_EVENT_INTEGRATION_V1_OK"
