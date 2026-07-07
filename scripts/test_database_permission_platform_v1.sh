#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_DATABASE_PERMISSION_PLATFORM_V1 ==="

sudo -u postgres psql -v ON_ERROR_STOP=1 -d finam_core -f sql/000_database_permission_platform_v1.sql

PYTHONPATH=src python - <<'PY'
import os
import psycopg2

conn = psycopg2.connect(os.getenv("DATABASE_URL", "postgresql:///finam_core"))
cur = conn.cursor()
cur.execute("""
SELECT
  current_user,
  has_schema_privilege(current_user,'analytics','USAGE'),
  has_schema_privilege(current_user,'presentation','USAGE'),
  has_table_privilege(current_user,'presentation.command_queue_v1','INSERT')
""")
row = cur.fetchone()
print(row)
assert row[1] is True
assert row[2] is True
assert row[3] is True
conn.close()
PY

echo "VERDICT=DATABASE_PERMISSION_PLATFORM_V1_READY"
echo "VERDICT=TEST_DATABASE_PERMISSION_PLATFORM_V1_OK"
