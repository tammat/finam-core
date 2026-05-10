#!/usr/bin/env bash
set -euo pipefail

export DATABASE_URL="${DATABASE_URL:-postgresql://finam:finam@localhost:5432/finam_core}"

# warn | fail
MODE="${1:-warn}"

python - <<PY
import os
import sys
import psycopg2

database_url = os.environ["DATABASE_URL"]
mode = "${MODE}"

with psycopg2.connect(database_url) as conn:
    with conn.cursor() as cur:
        cur.execute("""
            SELECT count(*)
            FROM event_dead_letters
            WHERE resolved = false
        """)
        unresolved = int(cur.fetchone()[0])

        cur.execute("""
            SELECT id, event_id, event_type, error_type, worker_name, created_at
            FROM event_dead_letters
            WHERE resolved = false
            ORDER BY id DESC
            LIMIT 5
        """)
        recent = cur.fetchall()

if unresolved > 0:
    print(
        "DLQ_HEALTH_WARNING "
        f"unresolved={unresolved} "
        f"mode={mode} "
        f"recent={recent}"
    )
    if mode == "fail":
        sys.exit(2)
else:
    print("DLQ_HEALTH_OK unresolved=0")
PY
