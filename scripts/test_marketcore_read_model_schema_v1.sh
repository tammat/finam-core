#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_MARKETCORE_READ_MODEL_SCHEMA_V1 ==="

psql finam_core <<'SQL'

SELECT schemaname,tablename
FROM pg_tables
WHERE schemaname='marketcore_ui'
ORDER BY tablename;

SQL

EXPECTED=5

FOUND=$(psql -At finam_core -c "
SELECT count(*)
FROM pg_tables
WHERE schemaname='marketcore_ui';
")

if [ "$FOUND" -ne "$EXPECTED" ]; then
    echo "EXPECTED=$EXPECTED"
    echo "FOUND=$FOUND"
    exit 1
fi

echo "tables=$FOUND"

echo "VERDICT=MARKETCORE_READ_MODEL_SCHEMA_V1_READY"

echo "TEST_MARKETCORE_READ_MODEL_SCHEMA_V1_OK"
