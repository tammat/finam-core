#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile \
  src/finam_core/reconciliation/manual_trade_reconciliation.py \
  src/finam_core/reconciliation/manual_position_snapshot_repository.py

sudo -u postgres env PYTHONPATH=src /opt/finam-core/.venv/bin/python - <<'PY'
import psycopg2

from finam_core.reconciliation.manual_trade_reconciliation import BrokerPositionSnapshot
from finam_core.reconciliation.manual_position_snapshot_repository import ManualPositionSnapshotRepository

conn = psycopg2.connect(dbname="finam_core")
repo = ManualPositionSnapshotRepository(conn)

count = repo.save_positions([
    BrokerPositionSnapshot(
        symbol="TEST@MOCK",
        qty=1.0,
        average_price=100.0,
        current_price=101.0,
        unrealized_pnl=1.0,
    )
])

assert count == 1
print("OK: saved manual broker position snapshot")
PY

sudo -u postgres psql -d finam_core -c "
SELECT id, created_at, symbol, qty, average_price, current_price, unrealized_pnl, source
FROM manual_broker_position_snapshots
ORDER BY id DESC
LIMIT 5;
"
