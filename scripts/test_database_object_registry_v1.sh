#!/usr/bin/env bash
set -euo pipefail

cd "$(git rev-parse --show-toplevel)"
export PYTHONPATH=src

python3 -m py_compile \
  src/scripts/architecture/build_database_object_registry_v1.py

python3 \
  src/scripts/architecture/build_database_object_registry_v1.py \
  | tee /tmp/database_object_registry_v1.log

grep -q "DATABASE OBJECT REGISTRY V1" \
  /tmp/database_object_registry_v1.log

grep -q "DB_OBJECT_REGISTRY_TOTAL" \
  /tmp/database_object_registry_v1.log

grep -q "DB_OBJECT_REGISTRY_VERDICT" \
  /tmp/database_object_registry_v1.log

grep -q "DATABASE_OBJECT_REGISTRY_V1_OK" \
  /tmp/database_object_registry_v1.log

unsafe_rows=$(psql "$DATABASE_URL" -At -c "
select count(*)
from database_object_registry_v1
where runtime_allowed=true
   or execution_enabled=true;
")

echo "unsafe_registry_rows=${unsafe_rows}"

if [ "${unsafe_rows}" != "0" ]; then
  echo "FAIL: registry has runtime/execution enabled"
  exit 1
fi

registry_rows=$(psql "$DATABASE_URL" -At -c "
select count(*)
from database_object_registry_v1;
")

echo "registry_rows=${registry_rows}"

if [ "${registry_rows}" -lt "200" ]; then
  echo "FAIL: registry rows unexpectedly low"
  exit 1
fi

echo TEST_DATABASE_OBJECT_REGISTRY_V1_OK
