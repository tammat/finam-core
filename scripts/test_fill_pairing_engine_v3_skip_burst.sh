#!/usr/bin/env bash
set -euo pipefail

cd "$(git rev-parse --show-toplevel)"
export PYTHONPATH=src

python3 -m py_compile \
  src/scripts/research/build_fill_pairing_engine_v3.py

python3 src/scripts/research/build_fill_pairing_engine_v3.py \
  | tee /tmp/fill_pairing_engine_v3_skip_burst.log

grep -q "FILL_PAIRING_ENGINE_V3_SUMMARY" \
  /tmp/fill_pairing_engine_v3_skip_burst.log

grep -q "skipped_burst_chains=" \
  /tmp/fill_pairing_engine_v3_skip_burst.log

burst_rows=$(psql "$DATABASE_URL" -At -c "
with per_minute as (
    select
        symbol,
        strategy,
        timeframe,
        trade_source,
        date_trunc('minute', entry_ts) as minute_bucket,
        count(*) chains
    from closed_trade_chains_v3
    group by 1,2,3,4,5
)
select count(*)
from per_minute
where chains > 10;
")

echo "burst_rows_after_pairing=${burst_rows}"

if [ "${burst_rows}" != "0" ]; then
  echo "FAIL: closed_trade_chains_v3 still contains burst chains"
  exit 1
fi

unsafe_rows=$(psql "$DATABASE_URL" -At -c "
select count(*)
from closed_trade_chains_v3
where runtime_allowed=true
   or execution_enabled=true;
")

echo "unsafe_v3_chain_rows=${unsafe_rows}"

if [ "${unsafe_rows}" != "0" ]; then
  echo "FAIL: v3 chain has runtime/execution enabled"
  exit 1
fi

echo TEST_FILL_PAIRING_ENGINE_V3_SKIP_BURST_OK
