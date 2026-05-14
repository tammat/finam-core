#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src
export PAGER=cat
export PSQL_PAGER=cat

python -m py_compile src/finam_core/storage/postgres_logger.py

TEST_FILL_ID="db-payload-test-fill-001"

python - <<'PY'
from finam_core.storage.postgres_logger import PostgresLogger

logger = PostgresLogger()

logger.log_fill(
    symbol="BRM6@RTSX",
    side="BUY",
    qty=1,
    price=100,
    trade_id="db-payload-test-fill-001",
    execution_type="paper",
    commission=0.1,
    payload={
        "signal_id": "db-payload-test-signal-001",
        "strategy": "BR_CONSERVATIVE_BREAKOUT_M5",
        "horizon": "INTRADAY",
        "regime": "trend_high_vol",
        "timeframe": "M5",
    },
)
PY

psql "$DATABASE_URL" -P pager=off -v ON_ERROR_STOP=1 <<SQL
DO \$\$
DECLARE
    v_signal text;
    v_strategy text;
    v_regime text;
BEGIN
    SELECT
        payload->>'signal_id',
        payload->>'strategy',
        payload->>'regime'
    INTO v_signal, v_strategy, v_regime
    FROM trades
    WHERE fill_id = '$TEST_FILL_ID';

    IF v_signal <> 'db-payload-test-signal-001'
       OR v_strategy <> 'BR_CONSERVATIVE_BREAKOUT_M5'
       OR v_regime <> 'trend_high_vol' THEN
        RAISE EXCEPTION 'log_fill payload metadata failed signal=% strategy=% regime=%',
            v_signal, v_strategy, v_regime;
    END IF;
END \$\$;

DELETE FROM trades WHERE fill_id = '$TEST_FILL_ID';
DELETE FROM fills WHERE fill_id = '$TEST_FILL_ID';
SQL

echo "OK: postgres logger log_fill stores payload metadata"
