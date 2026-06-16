#!/usr/bin/env bash
set -euo pipefail

cd "$(git rev-parse --show-toplevel)"
export PYTHONPATH=src

python3 -m py_compile \
  src/scripts/research/build_sber_d1_shadow_accumulation_v1.py

python3 \
  src/scripts/research/build_sber_d1_shadow_accumulation_v1.py \
  | tee /tmp/sber_shadow_accumulation_v1.log

grep -q "SBER D1 SHADOW ACCUMULATION V1" \
  /tmp/sber_shadow_accumulation_v1.log

grep -q "SBER_D1_SHADOW_ACCUMULATION_V1_OK" \
  /tmp/sber_shadow_accumulation_v1.log

psql "$DATABASE_URL" -c "
select count(*) unsafe_rows
from sber_d1_shadow_accumulation_v1
where coalesce(runtime_allowed,false)=true
   or coalesce(execution_enabled,false)=true
   or coalesce(shadow_only,false)=false;
"

echo TEST_SBER_D1_SHADOW_ACCUMULATION_V1_OK
