#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core || exit 1

echo "=== TEST_MARKET_STATE_ENGINE_LIVE_SHADOW_FEED_IMPLEMENTATION_V1 ==="

python3 -m py_compile \
  src/finam_core/research/live_shadow_feed.py

PYTHONPATH=src python3 - <<'PY'
import os

from finam_core.research.live_shadow_feed import LiveShadowFeedProcessor

processor = LiveShadowFeedProcessor(database_url=os.environ["DATABASE_URL"])

event = {
    "symbol": "SBER@MISX",
    "asset_class": "EQUITY",
    "timeframe": "M5",
    "close": 300.0,
    "trend": "UP",
    "volatility": "HIGH",
    "session": "MOSCOW_DAY",
    "event_ts": "2026-06-25T12:10:00+00:00",
}

result = processor.process_live_event(event)
again = processor.process_live_event(event)

assert result["snapshot_id"] == again["snapshot_id"]
assert result["symbol"] == "SBER@MISX"
assert result["timeframe"] == "M5"
assert result["feed_mode"] == "live_shadow_copy_only"
assert result["db_update"] == 1
assert result["orders_sent"] == 0
assert result["runtime_changed"] == 0
assert result["execution_changed"] == 0
assert result["real_trading_enabled"] == 0
assert "TREND=UP" in result["canonical_signature"]
assert "VOLATILITY=HIGH" in result["canonical_signature"]

print("RESULT snapshot_id=" + str(result["snapshot_id"]))
print("RESULT canonical_signature=" + result["canonical_signature"])
print("RESULT compact_signature=" + result["compact_signature"])
print("RESULT quality=" + result["quality"])
print("feed_mode=" + result["feed_mode"])
print("db_update=1")
print("orders_sent=0")
print("runtime_changed=0")
print("execution_changed=0")
print("real_trading_enabled=0")
print("VERDICT=MARKET_STATE_ENGINE_LIVE_SHADOW_FEED_IMPLEMENTATION_OK")
PY

if grep -R "from .*execution\|import .*execution\|OrderClient\|broker_adapter\|real_trading_enabled *= *1" \
  src/finam_core/research/live_shadow_feed.py; then
  echo "FORBIDDEN_IMPORT_OR_REAL_TRADING_FLAG_FOUND"
  exit 1
fi

echo "TEST_MARKET_STATE_ENGINE_LIVE_SHADOW_FEED_IMPLEMENTATION_V1_OK"
