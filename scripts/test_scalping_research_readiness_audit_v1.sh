#!/usr/bin/env bash
set -euo pipefail

cd "$(git rev-parse --show-toplevel)"
export PYTHONPATH=src

python3 -m py_compile \
  src/scripts/research/build_scalping_research_readiness_audit_v1.py

python3 \
  src/scripts/research/build_scalping_research_readiness_audit_v1.py \
  | tee /tmp/scalping_research_readiness_audit_v1.log

grep -q "SCALPING RESEARCH READINESS AUDIT V1" \
  /tmp/scalping_research_readiness_audit_v1.log

grep -q "SCALPING_DATA_ROW" \
  /tmp/scalping_research_readiness_audit_v1.log

grep -q "SCALPING_SOURCE_ROW" \
  /tmp/scalping_research_readiness_audit_v1.log

grep -q "SCALPING_EXECUTION_ROW" \
  /tmp/scalping_research_readiness_audit_v1.log

grep -q "SCALPING_READINESS_VERDICT" \
  /tmp/scalping_research_readiness_audit_v1.log

grep -q "SCALPING_RESEARCH_READINESS_AUDIT_V1_OK" \
  /tmp/scalping_research_readiness_audit_v1.log

unsafe_rows=$(psql "$DATABASE_URL" -At -c "
select count(*)
from strategy_statistics_v3
where runtime_allowed=true
   or execution_enabled=true;
")

echo "unsafe_scalping_runtime_rows=${unsafe_rows}"

if [ "${unsafe_rows}" != "0" ]; then
  echo "FAIL: runtime/execution unexpectedly enabled"
  exit 1
fi

echo TEST_SCALPING_RESEARCH_READINESS_AUDIT_V1_OK
