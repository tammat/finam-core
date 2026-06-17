#!/usr/bin/env bash
set -euo pipefail

cd "$(git rev-parse --show-toplevel)"

python3 -m py_compile src/scripts/research/register_usdrubf_v3_rebuild_candidate_v1.py

python3 src/scripts/research/register_usdrubf_v3_rebuild_candidate_v1.py \
  | tee /tmp/usdrubf_v3_rebuild_candidate_register_v1.log

grep -q "USDRUBF_V3_REBUILD_CANDIDATE_REGISTER_V1_OK" /tmp/usdrubf_v3_rebuild_candidate_register_v1.log
grep -q "USDRUBF@RTSX" /tmp/usdrubf_v3_rebuild_candidate_register_v1.log
grep -q "USD_INTRADAY_REGIME" /tmp/usdrubf_v3_rebuild_candidate_register_v1.log

unsafe_rows=$(psql "$DATABASE_URL" -At -c "
select count(*)
from rebuild_candidates_v1
where symbol='USDRUBF@RTSX'
  and strategy='USD_INTRADAY_REGIME'
  and timeframe='M5'
  and trade_source='paper'
  and (
       rebuild_status <> 'PLANNED'
    or rebuild_action <> 'REBUILD_V3'
    or quarantine_status <> 'ACTIVE'
    or runtime_allowed = true
    or execution_enabled = true
  );
")

echo "unsafe_usdrubf_rebuild_candidate_rows=${unsafe_rows}"

if [ "${unsafe_rows}" != "0" ]; then
  echo "FAIL: unsafe USDRUBF rebuild candidate"
  exit 1
fi

echo TEST_USDRUBF_V3_REBUILD_CANDIDATE_REGISTER_V1_OK
