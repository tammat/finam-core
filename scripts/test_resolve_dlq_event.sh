#!/usr/bin/env bash
set -euo pipefail

export DATABASE_URL="${DATABASE_URL:-postgresql://finam:finam@localhost:5432/finam_core}"

test -x scripts/resolve_dlq_event.sh

grep -q "event_dead_letters" scripts/resolve_dlq_event.sh
grep -q "SET resolved = true" scripts/resolve_dlq_event.sh
grep -q "DLQ_RESOLVED" scripts/resolve_dlq_event.sh
grep -q "DLQ_ALREADY_RESOLVED" scripts/resolve_dlq_event.sh

echo "DLQ_RESOLVE_SCRIPT_OK"
