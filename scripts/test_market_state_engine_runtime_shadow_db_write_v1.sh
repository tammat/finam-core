#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core || exit 1

echo "=== TEST_MARKET_STATE_ENGINE_RUNTIME_SHADOW_DB_WRITE_V1 ==="

python3 -m py_compile \
  src/finam_core/research/runtime_shadow_db_pipeline.py

PYTHONPATH=src python3 - <<'PY'
from datetime import datetime, timezone

from finam_core.research.runtime_shadow_db_pipeline import RuntimeShadowDbPipeline

import os

pipeline = RuntimeShadowDbPipeline(database_url=os.environ["DATABASE_URL"])

event = {
    "symbol": "SBER@MISX",
    "asset_class": "EQUITY",
    "timeframe": "M5",
    "close": 300.0,
    "trend": "UP",
    "volatility": "HIGH",
    "session": "MOSCOW_DAY",
}

result = pipeline.process_market_event(
    event,
    snapshot_ts=datetime(2026, 6, 25, 12, 5, 0, tzinfo=timezone.utc),
)

again = pipeline.process_market_event(
    event,
    snapshot_ts=datetime(2026, 6, 25, 12, 5, 0, tzinfo=timezone.utc),
)

assert result["snapshot_id"] == again["snapshot_id"]
assert result["symbol"] == "SBER@MISX"
assert result["timeframe"] == "M5"
assert "TREND=UP" in result["canonical_signature"]
assert "VOLATILITY=HIGH" in result["canonical_signature"]
assert result["compact_signature"].startswith("MS-")
assert result["quality"] == "GOOD"
assert result["orders_sent"] == 0
assert result["buy_sell_hold_decision"] == "NONE"
assert result["runtime_changed"] == 0
assert result["execution_changed"] == 0
assert result["real_trading_enabled"] == 0

print("RESULT snapshot_id=" + str(result["snapshot_id"]))
print("RESULT canonical_signature=" + result["canonical_signature"])
print("RESULT compact_signature=" + result["compact_signature"])
print("RESULT quality=" + result["quality"])
print("db_update=1")
print("orders_sent=0")
print("runtime_changed=0")
print("execution_changed=0")
print("real_trading_enabled=0")
print("VERDICT=MARKET_STATE_ENGINE_RUNTIME_SHADOW_DB_WRITE_OK")
PY

if grep -R "from .*execution\|import .*execution\|OrderClient\|broker_adapter\|real_trading_enabled *= *1" \
  src/finam_core/research/runtime_shadow_db_pipeline.py; then
  echo "FORBIDDEN_IMPORT_OR_REAL_TRADING_FLAG_FOUND"
  exit 1
fi

echo "TEST_MARKET_STATE_ENGINE_RUNTIME_SHADOW_DB_WRITE_V1_OK"
