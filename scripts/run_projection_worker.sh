#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH="${PYTHONPATH:-src}"
export DATABASE_URL="${DATABASE_URL:-postgresql://finam:finam@localhost:5432/finam_core}"

CHECKPOINT_NAME="${1:-projection_worker}"

python - <<PY
from finam_core.projections.projection_worker import ProjectionWorker

worker = ProjectionWorker(
    checkpoint_name="${CHECKPOINT_NAME}",
)

worker.run_forever()
PY
