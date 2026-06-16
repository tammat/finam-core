#!/usr/bin/env bash
set -euo pipefail

cd "$(git rev-parse --show-toplevel)"
export PYTHONPATH=src

python3 -m py_compile src/scripts/research/register_gold_v3_rebuild_candidate_v1.py

python3 src/scripts/research/register_gold_v3_rebuild_candidate_v1.py \
  | tee /tmp/gold_v3_rebuild_candidate_register_v1.log

grep -q "GOLD_V3_REBUILD_CANDIDATE_REGISTER_V1_OK" /tmp/gold_v3_rebuild_candidate_register_v1.log
grep -q "GDU6@RTSX" /tmp/gold_v3_rebuild_candidate_register_v1.log
grep -q "gold_short_only_shadow_v1" /tmp/gold_v3_rebuild_candidate_register_v1.log
grep -q "quarantine_status=ACTIVE" /tmp/gold_v3_rebuild_candidate_register_v1.log
grep -q "rebuild_action=REBUILD_V3" /tmp/gold_v3_rebuild_candidate_register_v1.log

unsafe_rows=$(psql "$DATABASE_URL" -At -c "
select count(*)
from rebuild_candidates_v1
where symbol='GDU6@RTSX'
  and strategy='gold_short_only_shadow_v1'
  and timeframe='M5'
  and trade_source='paper'
  and (
       rebuild_status <> 'PLANNED'
    or quarantine_status <> 'ACTIVE'
    or rebuild_action <> 'REBUILD_V3'
    or rebuild_reason <> 'gold_short_only_clean_paper_v3_rebuild'
    or runtime_allowed = true
    or execution_enabled = true
  );
")

echo "unsafe_gold_rebuild_candidate_rows=${unsafe_rows}"

if [ "${unsafe_rows}" != "0" ]; then
  echo "FAIL: unsafe gold rebuild candidate row"
  exit 1
fi

echo TEST_GOLD_V3_REBUILD_CANDIDATE_REGISTER_V1_OK
