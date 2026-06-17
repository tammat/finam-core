#!/usr/bin/env bash
set -euo pipefail

cd "$(git rev-parse --show-toplevel)"

python3 -m py_compile src/scripts/research/register_ng_multi_contract_v3_candidates_v1.py

python3 src/scripts/research/register_ng_multi_contract_v3_candidates_v1.py \
  | tee /tmp/ng_multi_contract_v3_candidates_v1.log

grep -q "NG_MULTI_CONTRACT_V3_CANDIDATES_V1_OK" /tmp/ng_multi_contract_v3_candidates_v1.log
grep -q "NGM6@RTSX" /tmp/ng_multi_contract_v3_candidates_v1.log
grep -q "NGQ6@RTSX" /tmp/ng_multi_contract_v3_candidates_v1.log
grep -q "NG_CONSERVATIVE_BREAKOUT_M1" /tmp/ng_multi_contract_v3_candidates_v1.log

unsafe_rows=$(psql "$DATABASE_URL" -At -c "
select count(*)
from rebuild_candidates_v1
where symbol in ('NGM6@RTSX','NGQ6@RTSX')
  and strategy in ('NG_CONSERVATIVE_BREAKOUT','NG_CONSERVATIVE_BREAKOUT_M1')
  and (
       rebuild_status <> 'PLANNED'
    or rebuild_action <> 'REBUILD_V3'
    or quarantine_status <> 'ACTIVE'
    or runtime_allowed = true
    or execution_enabled = true
  );
")

echo "unsafe_ng_multi_contract_candidate_rows=${unsafe_rows}"

if [ "${unsafe_rows}" != "0" ]; then
  echo "FAIL: unsafe NG multi-contract candidate rows"
  exit 1
fi

echo TEST_NG_MULTI_CONTRACT_V3_CANDIDATES_V1_OK
