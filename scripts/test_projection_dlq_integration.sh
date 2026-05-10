#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src
export DATABASE_URL="${DATABASE_URL:-postgresql://finam:finam@localhost:5432/finam_core}"

python - <<'PY'
from finam_core.events.dead_letter_service import DeadLetterService
from finam_core.events.event_store import StoredEvent
from finam_core.projections.projection_engine import ProjectionEngine


dlq = DeadLetterService()
before = dlq.unresolved_count()

engine = ProjectionEngine(
    dead_letters=dlq,
    worker_name="projection_dlq_test",
    strict=False,
)

state = engine.empty_state()

broken = StoredEvent(
    db_id=999998,
    event_id="evt_projection_broken_price",
    event_type="PIPE_FILLED",
    aggregate_type="portfolio",
    aggregate_id="dlq_projection_test",
    source="test",
    payload={
        "symbol": "NGH6@RTSX",
        "side": "BUY",
        "qty": 1.0,
        "price": "BROKEN_PRICE",
    },
)

engine.apply_event(state, broken)

after = dlq.unresolved_count()

assert after == before + 1, (before, after)
assert state.events_processed == 1, state

print("PROJECTION_DLQ_INTEGRATION_OK")
PY
