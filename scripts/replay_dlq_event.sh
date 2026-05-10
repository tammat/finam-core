#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH="${PYTHONPATH:-src}"
export DATABASE_URL="${DATABASE_URL:-postgresql://finam:finam@localhost:5432/finam_core}"

DLQ_ID="${1:-}"

if [ -z "${DLQ_ID}" ]; then
  echo "USAGE: bash scripts/replay_dlq_event.sh <dlq_id>"
  exit 1
fi

python - <<PY
import sys
from finam_core.events.dead_letter_replay_service import DeadLetterReplayService

service = DeadLetterReplayService()

try:
    result = service.replay_one(dlq_id=int("${DLQ_ID}"))
except Exception as exc:
    print(f"DLQ_REPLAY_FAIL id=${DLQ_ID} error={exc}")
    sys.exit(2)

if not result.ok:
    print(f"DLQ_REPLAY_FAIL id={result.id} reason={result.reason}")
    sys.exit(3)

print(
    f"DLQ_REPLAY_OK id={result.id} "
    f"event_id={result.event_id} reason={result.reason}"
)
PY
