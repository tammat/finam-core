#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src
export DATABASE_URL="${DATABASE_URL:-postgresql://finam:finam@localhost:5432/finam_core}"

python - <<'PY'
from finam_core.events.dead_letter_service import DeadLetterService
from finam_core.events.event_store import StoredEvent

dlq = DeadLetterService()
before = dlq.unresolved_count()

event = StoredEvent(
    db_id=999999,
    event_id="evt_dlq_test",
    event_type="BROKEN_EVENT",
    aggregate_type="test",
    aggregate_id="dlq_test",
    source="test",
    payload={"bad": "payload"},
)

try:
    raise ValueError("test broken event")
except Exception as exc:
    record = dlq.record_event_failure(
        event=event,
        error=exc,
        worker_name="test_worker",
    )

after = dlq.unresolved_count()

assert record.event_id == "evt_dlq_test", record
assert record.event_type == "BROKEN_EVENT", record
assert record.error_type == "ValueError", record
assert after == before + 1, (before, after)

print("DEAD_LETTER_SERVICE_OK", record.id)
PY
