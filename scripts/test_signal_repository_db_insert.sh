#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

sudo -u postgres env PYTHONPATH=src /opt/finam-core/.venv/bin/python - <<'PY'
import psycopg2

from finam_core.analytics.signal_repository import SignalRepository

conn = psycopg2.connect(dbname="finam_core")

repo = SignalRepository(conn)

signal_id = repo.save_signal({
    "symbol": "TEST@MOCK",
    "side": "BUY",
    "strategy": "test",
    "horizon": "SCALP",
    "timeframe": "M1",
    "price": 100.0,
    "stop_loss": 99.0,
    "take_profit": 102.0,
    "confidence": 0.5,
})

print("OK signal_id=", signal_id)
PY

sudo -u postgres psql -d finam_core -c "
SELECT id, signal_id, created_at, symbol, side, horizon,
       entry_price, stop_loss, take_profit, rr, status
FROM signals
WHERE symbol = 'TEST@MOCK'
ORDER BY id DESC
LIMIT 5;
"
