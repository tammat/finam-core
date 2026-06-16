#!/usr/bin/env bash
set -euo pipefail

cd "$(git rev-parse --show-toplevel)"
export PYTHONPATH=src

python3 -m py_compile \
  src/scripts/research/build_trade_attribution_v3_from_chains_v3.py

python3 \
  src/scripts/research/build_fill_pairing_engine_v3.py \
  | tee /tmp/fill_pairing_engine_v3_before_attr.log

python3 \
  src/scripts/research/build_trade_attribution_v3_from_chains_v3.py \
  | tee /tmp/trade_attribution_v3_from_chains_v3.log

grep -q "TRADE ATTRIBUTION V3 FROM CHAINS V3" \
  /tmp/trade_attribution_v3_from_chains_v3.log

grep -q "TRADE_ATTRIBUTION_V3_SUMMARY" \
  /tmp/trade_attribution_v3_from_chains_v3.log

grep -q "TRADE_ATTRIBUTION_V3_FROM_CHAINS_V3_OK" \
  /tmp/trade_attribution_v3_from_chains_v3.log

unsafe_rows=$(psql "$DATABASE_URL" -At -c "
select count(*)
from trade_attribution_v3
where runtime_allowed=true
   or execution_enabled=true;
")

echo "unsafe_trade_attribution_v3_rows=${unsafe_rows}"

if [ "${unsafe_rows}" != "0" ]; then
  echo "FAIL: trade_attribution_v3 has runtime/execution enabled"
  exit 1
fi

symbol_only_rows=$(psql "$DATABASE_URL" -At -c "
select count(*)
from trade_attribution_v3
where coalesce(strategy,'')=''
   or coalesce(timeframe,'')='';
")

echo "symbol_only_trade_attribution_v3_rows=${symbol_only_rows}"

if [ "${symbol_only_rows}" != "0" ]; then
  echo "FAIL: trade_attribution_v3 contains symbol-only attribution"
  exit 1
fi

orphan_rows=$(psql "$DATABASE_URL" -At -c "
select count(*)
from trade_attribution_v3 a
left join closed_trade_chains_v3 c
  on c.id=a.chain_v3_id
where c.id is null;
")

echo "orphan_trade_attribution_v3_rows=${orphan_rows}"

if [ "${orphan_rows}" != "0" ]; then
  echo "FAIL: trade_attribution_v3 contains orphan chain references"
  exit 1
fi

echo TEST_TRADE_ATTRIBUTION_V3_FROM_CHAINS_V3_OK
