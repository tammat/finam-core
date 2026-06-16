#!/usr/bin/env bash
set -euo pipefail

cd "$(git rev-parse --show-toplevel)"
export PYTHONPATH=src

python3 -m py_compile \
  src/scripts/research/build_clean_paper_accumulation_tracker_v1.py

python3 \
  src/scripts/research/build_clean_paper_accumulation_tracker_v1.py \
  | tee /tmp/clean_paper_accumulation_tracker_v1.log

grep -q "CLEAN PAPER ACCUMULATION TRACKER V1" \
  /tmp/clean_paper_accumulation_tracker_v1.log

grep -q "CLEAN_PAPER_ACCUMULATION_TRACKER_V1_OK" \
  /tmp/clean_paper_accumulation_tracker_v1.log

unsafe_rows=$(psql "$DATABASE_URL" -At -c "
select count(*)
from clean_paper_accumulation_tracker_v1
where runtime_allowed=true
   or execution_enabled=true;
")

echo "unsafe_clean_paper_accumulation_rows=${unsafe_rows}"

if [ "${unsafe_rows}" != "0" ]; then
  echo "FAIL: clean paper tracker enabled runtime/execution"
  exit 1
fi

echo TEST_CLEAN_PAPER_ACCUMULATION_TRACKER_V1_OK
