#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src
export DATABASE_URL="${DATABASE_URL:-postgresql://finam:finam@localhost:5432/finam_core}"

python - <<'PY'
import time

from finam_core.projections.projection_checkpoint_service import ProjectionCheckpointService

service = ProjectionCheckpointService()
name = f"checkpoint_test_{time.time_ns()}"

initial = service.get(name=name)
assert initial.last_event_id == 0, initial

updated = service.update(name=name, last_event_id=10)
assert updated.last_event_id == 10, updated

# Русский комментарий: offset не должен откатываться назад.
older = service.update(name=name, last_event_id=5)
assert older.last_event_id == 10, older

newer = service.update(name=name, last_event_id=25)
assert newer.last_event_id == 25, newer

loaded = service.get(name=name)
assert loaded.last_event_id == 25, loaded

print("PROJECTION_CHECKPOINT_SERVICE_OK", name)
PY
