#!/usr/bin/env bash
set -euo pipefail

cd "$(git rev-parse --show-toplevel)"
export PYTHONPATH=src

python3 -m py_compile \
  src/scripts/architecture/build_database_object_registry_review_plan_v1.py

python3 \
  src/scripts/architecture/build_database_object_registry_review_plan_v1.py \
  | tee /tmp/database_object_registry_review_plan_v1.log

grep -q "DATABASE OBJECT REGISTRY REVIEW PLAN V1" \
  /tmp/database_object_registry_review_plan_v1.log

grep -q "DB_REGISTRY_REVIEW_PLAN_TOTAL" \
  /tmp/database_object_registry_review_plan_v1.log

grep -q "DB_REGISTRY_REVIEW_PLAN_VERDICT" \
  /tmp/database_object_registry_review_plan_v1.log

grep -q "DATABASE_OBJECT_REGISTRY_REVIEW_PLAN_V1_OK" \
  /tmp/database_object_registry_review_plan_v1.log

unsafe_rows=$(psql "$DATABASE_URL" -At -c "
select count(*)
from database_object_registry_review_plan_v1
where runtime_allowed=true
   or execution_enabled=true;
")

echo "unsafe_registry_review_rows=${unsafe_rows}"

if [ "${unsafe_rows}" != "0" ]; then
  echo "FAIL: registry review plan has runtime/execution enabled"
  exit 1
fi

drop_rows=$(psql "$DATABASE_URL" -At -c "
select count(*)
from database_object_registry_review_plan_v1
where proposed_action='DROP_CANDIDATE';
")

echo "drop_candidate_rows=${drop_rows}"

if [ "${drop_rows}" != "0" ]; then
  echo "FAIL: review plan proposed DROP_CANDIDATE too early"
  exit 1
fi

echo TEST_DATABASE_OBJECT_REGISTRY_REVIEW_PLAN_V1_OK
