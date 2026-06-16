#!/usr/bin/env bash
set -euo pipefail

cd "$(git rev-parse --show-toplevel)"
export PYTHONPATH=src

python3 -m py_compile \
  src/scripts/research/build_paper_source_cleanup_plan_v1.py

python3 \
  src/scripts/research/build_paper_source_cleanup_plan_v1.py

psql "$DATABASE_URL" -c "
select
    source_status,
    cleanup_action,
    rows_count
from paper_source_cleanup_plan_v1
order by rows_count desc;
"

unsafe_rows=$(psql "$DATABASE_URL" -At -c "
select count(*)
from paper_source_cleanup_plan_v1
where runtime_allowed=true;
")

echo "unsafe_runtime_rows=${unsafe_rows}"

if [ "${unsafe_rows}" != "0" ]; then
    echo FAIL
    exit 1
fi

echo TEST_PAPER_SOURCE_CLEANUP_PLAN_V1_OK
