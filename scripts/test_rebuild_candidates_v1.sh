#!/usr/bin/env bash
set -euo pipefail

cd "$(git rev-parse --show-toplevel)"
export PYTHONPATH=src

python3 -m py_compile \
  src/scripts/research/build_rebuild_candidates_v1.py

python3 \
  src/scripts/research/build_rebuild_candidates_v1.py \
  | tee /tmp/rebuild_candidates_v1.log

grep -q "REBUILD CANDIDATES V1" \
  /tmp/rebuild_candidates_v1.log

grep -q "REBUILD_CANDIDATES_SUMMARY" \
  /tmp/rebuild_candidates_v1.log

grep -q "REBUILD_CANDIDATES_V1_OK" \
  /tmp/rebuild_candidates_v1.log

unsafe_rows=$(psql "$DATABASE_URL" -At -c "
select count(*)
from rebuild_candidates_v1
where runtime_allowed=true
   or execution_enabled=true;
")

echo "unsafe_rebuild_candidate_rows=${unsafe_rows}"

if [ "${unsafe_rows}" != "0" ]; then
  echo "FAIL: rebuild candidate has runtime/execution enabled"
  exit 1
fi

planned_rows=$(psql "$DATABASE_URL" -At -c "
select count(*)
from rebuild_candidates_v1
where rebuild_status='PLANNED';
")

echo "planned_rebuild_rows=${planned_rows}"

if [ "${planned_rows}" != "8" ]; then
  echo "FAIL: expected 8 rebuild candidates"
  exit 1
fi

echo TEST_REBUILD_CANDIDATES_V1_OK
