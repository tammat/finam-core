#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH="${PYTHONPATH:-src}"
export DATABASE_URL="${DATABASE_URL:-postgresql://finam:finam@localhost:5432/finam_core}"

BATCH_SIZE="${1:-10000}"

python - <<PY
from finam_core.projections.projection_updater import ProjectionUpdater

updater = ProjectionUpdater()

result = updater.update_all(
    batch_size=int("${BATCH_SIZE}")
)

print(
    "PROJECTION_UPDATE_OK "
    f"events_loaded={result.events_loaded} "
    f"events_processed={result.events_processed} "
    f"orders={result.orders_count} "
    f"positions={result.positions_count}"
)
PY
