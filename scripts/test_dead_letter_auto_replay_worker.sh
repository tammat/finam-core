#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src
export DATABASE_URL="${DATABASE_URL:-postgresql://finam:finam@localhost:5432/finam_core}"

python - <<'PY'
import time
import psycopg2
import psycopg2.extras

from finam_core.events.dead_letter_auto_replay_worker import DeadLetterAutoReplayWorker
from finam_core.events.dead_letter_service import DeadLetterService
from finam_core.events.event_store import StoredEvent
from finam_core.projections.projection_store import ProjectionStore

dlq = DeadLetterService()
projection_store = ProjectionStore()

aggregate_id = f"dlq_auto_replay_{time.time_ns()}"
symbol = f"DLQAUTO{time.time_ns()}@RTSX"

event = StoredEvent(
    db_id=888001,
    event_id=f"evt_{aggregate_id}",
    event_type="PIPE_FILLED",
    aggregate_type="portfolio",
    aggregate_id=aggregate_id,
    source="test",
    payload={
        "symbol": symbol,
        "side": "BUY",
        "qty": 1.0,
        "price": 100.0,
    },
)

try:
    raise ValueError("temporary auto replay failure")
except Exception as exc:
    record = dlq.record_event_failure(
        event=event,
        error=exc,
        worker_name="dlq_auto_replay_test",
    )

worker = DeadLetterAutoReplayWorker(
    interval_sec=0.1,
    limit=100,
)

result = worker.tick()

assert result.ok is True, result
assert result.scanned >= 1, result
assert result.replayed >= 1, result

position = projection_store.get_position(symbol)
assert position is not None, position
assert abs(float(position["qty"]) - 1.0) < 0.000001, position

import os

database_url = os.environ["DATABASE_URL"]

with psycopg2.connect(database_url) as conn:
    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute(
            "SELECT resolved FROM event_dead_letters WHERE id = %s",
            (record.id,),
        )
        row = cur.fetchone()

assert row is not None
assert bool(row["resolved"]) is True, row

print("DLQ_AUTO_REPLAY_WORKER_OK", record.id)
PY
