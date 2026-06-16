#!/usr/bin/env bash
set -euo pipefail

cd "$(git rev-parse --show-toplevel)"
export PYTHONPATH=src

python3 -m py_compile src/scripts/research/run_gold_shadow_to_paper_accumulator_v1.py

python3 src/scripts/research/run_gold_shadow_to_paper_accumulator_v1.py --audit-only \
  | tee /tmp/gold_shadow_to_paper_accumulator_v1_audit.log

grep -q "GOLD_SHADOW_TO_PAPER_ACCUMULATOR_V1_OK" /tmp/gold_shadow_to_paper_accumulator_v1_audit.log
grep -q "runtime_allow=0" /tmp/gold_shadow_to_paper_accumulator_v1_audit.log
grep -q "execution_enabled=0" /tmp/gold_shadow_to_paper_accumulator_v1_audit.log

unsafe_rows=$(psql "$DATABASE_URL" -At -c "
select count(*)
from gold_shadow_to_paper_accumulation_audit_v1
where runtime_allowed = true
   or execution_enabled = true
   or symbol <> 'GDU6@RTSX'
   or strategy <> 'gold_short_only_shadow_v1'
   or timeframe <> 'M5'
   or side <> 'SELL';
")

echo "unsafe_gold_accumulation_rows=${unsafe_rows}"

if [ "${unsafe_rows}" != "0" ]; then
  echo "FAIL: unsafe gold accumulation rows"
  exit 1
fi

python3 src/scripts/research/run_gold_shadow_to_paper_accumulator_v1.py \
  | tee /tmp/gold_shadow_to_paper_accumulator_v1_apply.log

grep -q "GOLD_SHADOW_TO_PAPER_ACCUMULATOR_V1_OK" /tmp/gold_shadow_to_paper_accumulator_v1_apply.log

bad_trades=$(psql "$DATABASE_URL" -At -c "
select count(*)
from trades t
join gold_shadow_to_paper_accumulation_audit_v1 a
  on a.paper_trade_id = t.id
where (
       t.origin <> 'paper'
    or t.trade_source <> 'paper'
    or t.symbol <> 'GDU6@RTSX'
    or t.strategy <> 'gold_short_only_shadow_v1'
    or t.timeframe <> 'M5'
    or t.side <> 'SELL'
);
")

echo "bad_gold_paper_trades=${bad_trades}"

if [ "${bad_trades}" != "0" ]; then
  echo "FAIL: bad gold paper trades created"
  exit 1
fi

echo TEST_GOLD_SHADOW_TO_PAPER_ACCUMULATOR_V1_OK
