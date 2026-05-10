#!/usr/bin/env bash
set -euo pipefail

export DATABASE_URL="${DATABASE_URL:-postgresql://finam:finam@localhost:5432/finam_core}"
export PYTHON_BIN="${PYTHON_BIN:-/opt/finam-core/.venv/bin/python}"

"${PYTHON_BIN}" - <<'PY'
import os
import psycopg2
import psycopg2.extras

database_url = os.environ["DATABASE_URL"]

with psycopg2.connect(database_url) as conn:
    with conn.cursor() as cur:
        with open("sql/20260510_production_dashboard_views.sql", "r", encoding="utf-8") as f:
            cur.execute(f.read())

    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        print("=== PRODUCTION HEALTH ===")
        cur.execute("SELECT * FROM v_production_health")
        print(dict(cur.fetchone()))

        print("\n=== POSITIONS ===")
        cur.execute("SELECT * FROM v_positions_dashboard LIMIT 20")
        for row in cur.fetchall():
            print(dict(row))

        print("\n=== ORDERS LAST 20 ===")
        cur.execute("SELECT * FROM v_orders_dashboard LIMIT 20")
        for row in cur.fetchall():
            print(dict(row))

        print("\n=== DLQ LAST 20 ===")
        cur.execute("SELECT * FROM v_dlq_dashboard LIMIT 20")
        for row in cur.fetchall():
            print(dict(row))

print("PRODUCTION_DASHBOARD_OK")
PY
