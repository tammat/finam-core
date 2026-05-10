#!/usr/bin/env bash
set -euo pipefail

export DATABASE_URL="${DATABASE_URL:-postgresql://finam:finam@localhost:5432/finam_core}"

SERVICE="${1:-finam-projection-worker.service}"
CHECKPOINT_NAME="${2:-projection_worker}"
MAX_AGE_SEC="${3:-120}"

if ! systemctl is-active --quiet "${SERVICE}"; then
  echo "PROJECTION_WORKER_HEALTH_FAIL reason=service_not_active service=${SERVICE}"
  exit 1
fi

python - <<PY
import os
import sys
import time
import psycopg2

database_url = os.environ["DATABASE_URL"]
checkpoint_name = "${CHECKPOINT_NAME}"
max_age_sec = int("${MAX_AGE_SEC}")

with psycopg2.connect(database_url) as conn:
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT last_event_id, EXTRACT(EPOCH FROM (now() - updated_at))::int AS age_sec
            FROM projection_checkpoints
            WHERE name = %s
            """,
            (checkpoint_name,),
        )
        row = cur.fetchone()

        if row is None:
            print(f"PROJECTION_WORKER_HEALTH_FAIL reason=checkpoint_missing checkpoint={checkpoint_name}")
            sys.exit(2)

        last_event_id, age_sec = int(row[0]), int(row[1])

        stale_warning = ""
        if age_sec > max_age_sec:
            stale_warning = f" warning=checkpoint_stale age_sec={age_sec} max_age_sec={max_age_sec}"

        cur.execute("SELECT count(*) FROM portfolio_projection")
        portfolio_count = int(cur.fetchone()[0])

        cur.execute("SELECT count(*) FROM order_projection")
        order_count = int(cur.fetchone()[0])

        cur.execute("SELECT count(*) FROM position_projection")
        position_count = int(cur.fetchone()[0])

        if portfolio_count <= 0:
            print("PROJECTION_WORKER_HEALTH_FAIL reason=portfolio_projection_empty")
            sys.exit(4)

        print(
            "PROJECTION_WORKER_HEALTH_OK "
            f"service=${SERVICE} "
            f"checkpoint={checkpoint_name} "
            f"last_event_id={last_event_id} "
            f"age_sec={age_sec} "
            f"orders={order_count} "
            f"positions={position_count} "
            f"portfolio={portfolio_count}"
            f"{stale_warning}"
        )
PY
