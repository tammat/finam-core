#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src
export PAGER=cat
export PSQL_PAGER=cat

FILL_ID="runtime-fill-$(date +%s)"

python - <<PY
from finam_core.storage.postgres_logger import PostgresLogger

pg = PostgresLogger()

payload = {
    "signal_id": "runtime-signal-001",
    "strategy": "BR_CONSERVATIVE_BREAKOUT_M5",
    "horizon": "INTRADAY",
    "regime": "trend_high_vol",
    "timeframe": "M5",
}

pg.log_fill(
    symbol="BRM6@RTSX",
    side="BUY",
    qty=1,
    price=100.0,
    commission=0.1,
    fill_id="${FILL_ID}",
    execution_type="runtime_test",
    payload=payload,
)

print("OK: runtime fill inserted")
PY

psql "$DATABASE_URL" -P pager=off -c "
select
    fill_id,
    payload->>'signal_id' as signal_id,
    payload->>'strategy' as strategy,
    payload->>'regime' as regime
from trades
where fill_id = '${FILL_ID}';
"

psql "$DATABASE_URL" -P pager=off -c "
delete from trades where fill_id = '${FILL_ID}';
delete from fills where fill_id = '${FILL_ID}';
"

echo "OK: runtime metadata insert verified and cleaned"
