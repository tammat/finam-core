#!/usr/bin/env bash
set -euo pipefail

cd "$(git rev-parse --show-toplevel)"
export PYTHONPATH=src

python3 -m py_compile \
  src/scripts/research/build_research_data_quality_gate_v1.py

python3 \
  src/scripts/research/build_research_data_quality_gate_v1.py \
  | tee /tmp/research_data_quality_gate_v1.log

grep -q "RESEARCH DATA QUALITY GATE V1" \
  /tmp/research_data_quality_gate_v1.log

grep -q "RESEARCH_DATA_QUALITY_GATE_SUMMARY" \
  /tmp/research_data_quality_gate_v1.log

grep -q "RESEARCH_DATA_QUALITY_GATE_V1_OK" \
  /tmp/research_data_quality_gate_v1.log

unsafe_rows=$(psql "$DATABASE_URL" -At -c "
select count(*)
from research_data_quality_gate_v1
where gate_status='BLOCKED'
  and (
       allow_statistics=true
    or allow_walkforward=true
    or allow_promotion=true
    or allow_runtime=true
    or runtime_allowed=true
    or execution_enabled=true
  );
")

echo "unsafe_blocked_rows=${unsafe_rows}"

if [ "${unsafe_rows}" != "0" ]; then
  echo "FAIL: blocked research data is still allowed downstream"
  exit 1
fi

echo TEST_RESEARCH_DATA_QUALITY_GATE_V1_OK
