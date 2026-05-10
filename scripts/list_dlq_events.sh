#!/usr/bin/env bash
set -euo pipefail

export DATABASE_URL="${DATABASE_URL:-postgresql://finam:finam@localhost:5432/finam_core}"

LIMIT="${1:-50}"

python - <<PY
import os
import psycopg2
import psycopg2.extras

database_url = os.environ["DATABASE_URL"]
limit = int("${LIMIT}")

with psycopg2.connect(database_url) as conn:
    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:

        cur.execute(
            """
            SELECT
                id,
                event_id,
                event_type,
                worker_name,
                error_type,
                resolved,
                created_at
            FROM event_dead_letters
            ORDER BY id DESC
            LIMIT %s
            """,
            (limit,),
        )

        rows = cur.fetchall()

if not rows:
    print("DLQ_EMPTY")
    raise SystemExit(0)

print(
    "id\tresolved\tevent_type\tworker\terror\tcreated_at\tevent_id"
)

for row in rows:
    print(
        f"{row['id']}\t"
        f"{row['resolved']}\t"
        f"{row['event_type']}\t"
        f"{row['worker_name']}\t"
        f"{row['error_type']}\t"
        f"{row['created_at']}\t"
        f"{row['event_id']}"
    )

print(f"DLQ_LIST_OK rows={len(rows)}")
PY
