#!/usr/bin/env bash
set -euo pipefail

cd "$(git rev-parse --show-toplevel)"
export PYTHONPATH=src

python3 -m py_compile \
  src/scripts/research/build_trusted_strategy_statistics_v1.py

python3 \
  src/scripts/research/build_trusted_strategy_statistics_v1.py \
  | tee /tmp/trusted_strategy_statistics_v1.log

grep -q "TRUSTED STRATEGY STATISTICS V1" \
  /tmp/trusted_strategy_statistics_v1.log

grep -q "TRUSTED_STRATEGY_STATISTICS_SUMMARY" \
  /tmp/trusted_strategy_statistics_v1.log

grep -q "runtime_allow=0" \
  /tmp/trusted_strategy_statistics_v1.log

grep -q "execution_enabled=0" \
  /tmp/trusted_strategy_statistics_v1.log

grep -q "TRUSTED_STRATEGY_STATISTICS_V1_OK" \
  /tmp/trusted_strategy_statistics_v1.log

psql "$DATABASE_URL" -c "
select count(*) unsafe_rows
from trusted_strategy_statistics_v1
where coalesce(runtime_allowed,false)=true
   or coalesce(execution_enabled,false)=true;
"

psql "$DATABASE_URL" -c "
select
    trusted_status,
    trusted_reason,
    count(*) rows
from trusted_strategy_statistics_v1
group by trusted_status, trusted_reason
order by trusted_status, rows desc;
"

echo TEST_TRUSTED_STRATEGY_STATISTICS_V1_OK
