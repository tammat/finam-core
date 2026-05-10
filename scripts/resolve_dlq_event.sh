#!/usr/bin/env bash
set -euo pipefail

export DATABASE_URL="${DATABASE_URL:-postgresql://finam:finam@localhost:5432/finam_core}"

DLQ_ID="${1:-}"

if [ -z "${DLQ_ID}" ]; then
  echo "USAGE: bash scripts/resolve_dlq_event.sh <dlq_id>"
  exit 1
fi

python - <<PY
import os
import sys
import psycopg2

database_url = os.environ["DATABASE_URL"]
dlq_id = int("${DLQ_ID}")

with psycopg2.connect(database_url) as conn:
    with conn.cursor() as cur:

        cur.execute("""
            SELECT resolved
            FROM event_dead_letters
            WHERE id = %s
        """, (dlq_id,))

        row = cur.fetchone()

        if row is None:
            print(f"DLQ_RESOLVE_FAIL reason=not_found id={dlq_id}")
            sys.exit(2)

        already_resolved = bool(row[0])

        if already_resolved:
            print(f"DLQ_ALREADY_RESOLVED id={dlq_id}")
            sys.exit(0)

        cur.execute("""
            UPDATE event_dead_letters
            SET resolved = true
            WHERE id = %s
        """, (dlq_id,))

print(f"DLQ_RESOLVED id={dlq_id}")
PY
