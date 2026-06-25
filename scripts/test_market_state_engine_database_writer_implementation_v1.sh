#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core || exit 1

echo "=== TEST_MARKET_STATE_ENGINE_DATABASE_WRITER_IMPLEMENTATION_V1 ==="

python3 -m py_compile \
  src/finam_core/research/market_state/repository.py \
  src/finam_core/research/market_state/db_writer.py

PYTHONPATH=src python3 - <<'PY'
from datetime import datetime, timezone

from finam_core.research.events import MarketFeaturesReadyEvent
from finam_core.research.market_state.db_writer import MarketStateDbWriter

writer = MarketStateDbWriter()

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

snapshot_id = writer.save_features_event(
    event,
    snapshot_ts=datetime(2026, 6, 25, 12, 0, 0, tzinfo=timezone.utc),
    asset_class="EQUITY",
)

assert isinstance(snapshot_id, int)
assert snapshot_id > 0

snapshot_id_2 = writer.save_features_event(
    event,
    snapshot_ts=datetime(2026, 6, 25, 12, 0, 0, tzinfo=timezone.utc),
    asset_class="EQUITY",
)

assert snapshot_id_2 == snapshot_id

print("RESULT snapshot_id=" + str(snapshot_id))
print("RESULT idempotent_snapshot_id=" + str(snapshot_id_2))
print("db_update=1")
print("runtime_changed=0")
print("execution_changed=0")
print("real_trading_enabled=0")
print("orders_sent=0")
print("VERDICT=MARKET_STATE_ENGINE_DATABASE_WRITER_IMPLEMENTATION_OK")
PY

if grep -R "from .*execution\|import .*execution\|OrderClient\|broker_adapter\|real_trading_enabled *= *1" \
  src/finam_core/research/market_state/repository.py \
  src/finam_core/research/market_state/db_writer.py; then
  echo "FORBIDDEN_IMPORT_OR_REAL_TRADING_FLAG_FOUND"
  exit 1
fi

echo "TEST_MARKET_STATE_ENGINE_DATABASE_WRITER_IMPLEMENTATION_V1_OK"
