#!/usr/bin/env bash
set -euo pipefail

cd "$(git rev-parse --show-toplevel)"
export PYTHONPATH=src

python3 -m py_compile \
  src/scripts/research/build_fill_pairing_engine_v3.py

python3 \
  src/scripts/research/build_fill_pairing_engine_v3.py \
  | tee /tmp/fill_pairing_engine_v3.log

grep -q "FILL PAIRING ENGINE V3" \
  /tmp/fill_pairing_engine_v3.log

grep -q "FILL_PAIRING_ENGINE_V3_SUMMARY" \
  /tmp/fill_pairing_engine_v3.log

grep -q "FILL_PAIRING_ENGINE_V3_OK" \
  /tmp/fill_pairing_engine_v3.log

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

symbol_only_rows=$(psql "$DATABASE_URL" -At -c "
select count(*)
from closed_trade_chains_v3
where coalesce(strategy,'')=''
   or coalesce(timeframe,'')='';
")

echo "symbol_only_v3_rows=${symbol_only_rows}"

if [ "${symbol_only_rows}" != "0" ]; then
  echo "FAIL: v3 contains symbol-only chains"
  exit 1
fi

echo TEST_FILL_PAIRING_ENGINE_V3_OK
