#!/usr/bin/env bash
set -euo pipefail

cd "$(git rev-parse --show-toplevel)"
export PYTHONPATH=src

python3 -m py_compile \
  src/scripts/research/build_strategy_statistics_v3_from_attribution_v3.py

python3 src/scripts/research/build_fill_pairing_engine_v3.py \
  | tee /tmp/fill_pairing_engine_v3_before_stats.log

python3 src/scripts/research/build_trade_attribution_v3_from_chains_v3.py \
  | tee /tmp/trade_attribution_v3_before_stats.log

python3 src/scripts/research/build_strategy_statistics_v3_from_attribution_v3.py \
  | tee /tmp/strategy_statistics_v3_from_attribution_v3.log

grep -q "STRATEGY STATISTICS V3 FROM ATTRIBUTION V3" \
  /tmp/strategy_statistics_v3_from_attribution_v3.log

grep -q "STRATEGY_STATISTICS_V3_SUMMARY" \
  /tmp/strategy_statistics_v3_from_attribution_v3.log

grep -q "STRATEGY_STATISTICS_V3_FROM_ATTRIBUTION_V3_OK" \
  /tmp/strategy_statistics_v3_from_attribution_v3.log

unsafe_rows=$(psql "$DATABASE_URL" -At -c "
select count(*)
from strategy_statistics_v3
where runtime_allowed=true
   or execution_enabled=true;
")

echo "unsafe_strategy_statistics_v3_rows=${unsafe_rows}"

if [ "${unsafe_rows}" != "0" ]; then
  echo "FAIL: strategy_statistics_v3 has runtime/execution enabled"
  exit 1
fi

symbol_only_rows=$(psql "$DATABASE_URL" -At -c "
select count(*)
from strategy_statistics_v3
where coalesce(strategy,'')=''
   or coalesce(timeframe,'')='';
")

echo "symbol_only_strategy_statistics_v3_rows=${symbol_only_rows}"

if [ "${symbol_only_rows}" != "0" ]; then
  echo "FAIL: strategy_statistics_v3 contains symbol-only statistics"
  exit 1
fi

echo TEST_STRATEGY_STATISTICS_V3_FROM_ATTRIBUTION_V3_OK
