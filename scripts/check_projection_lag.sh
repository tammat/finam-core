#!/usr/bin/env bash
set -euo pipefail

export DATABASE_URL="${DATABASE_URL:-postgresql://finam:finam@localhost:5432/finam_core}"

CHECKPOINT_NAME="${1:-projection_worker}"
MAX_LAG="${2:-100}"

python - <<PY
import os
import sys
import psycopg2

database_url = os.environ["DATABASE_URL"]
checkpoint_name = "${CHECKPOINT_NAME}"
max_lag = int("${MAX_LAG}")

with psycopg2.connect(database_url) as conn:
    with conn.cursor() as cur:
        cur.execute("SELECT COALESCE(max(id), 0) FROM event_store")
        latest_event_id = int(cur.fetchone()[0])

        cur.execute(
            """
            SELECT last_event_id
            FROM projection_checkpoints
            WHERE name = %s
            """,
            (checkpoint_name,),
        )
        row = cur.fetchone()

        if row is None:
            print(f"PROJECTION_LAG_FAIL reason=checkpoint_missing checkpoint={checkpoint_name}")
            sys.exit(2)

        checkpoint_event_id = int(row[0])
        lag = latest_event_id - checkpoint_event_id

        if lag > max_lag:
            print(
                f"PROJECTION_LAG_FAIL checkpoint={checkpoint_name} "
                f"latest_event_id={latest_event_id} "
                f"checkpoint_event_id={checkpoint_event_id} "
                f"lag={lag} max_lag={max_lag}"
            )
            sys.exit(3)

        print(
            f"PROJECTION_LAG_OK checkpoint={checkpoint_name} "
            f"latest_event_id={latest_event_id} "
            f"checkpoint_event_id={checkpoint_event_id} "
            f"lag={lag} max_lag={max_lag}"
        )
PY
