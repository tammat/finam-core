#!/usr/bin/env bash
set -euo pipefail

cd "$(git rev-parse --show-toplevel)"
export PYTHONPATH=src

python3 -m py_compile src/scripts/research/apply_gold_synthetic_exit_v1.py

python3 src/scripts/research/apply_gold_synthetic_exit_v1.py \
  | tee /tmp/gold_synthetic_exit_apply_v1.log

grep -q "GOLD_SYNTHETIC_EXIT_APPLY_V1_OK" /tmp/gold_synthetic_exit_apply_v1.log
grep -q "policy=TIME_EXIT_M5_12BARS" /tmp/gold_synthetic_exit_apply_v1.log

unsafe_rows=$(psql "$DATABASE_URL" -At -c "
select count(*)
from gold_synthetic_exit_policy_audit_v1 a
join trades t
  on t.id = a.synthetic_exit_trade_id
where a.exit_policy = 'TIME_EXIT_M5_12BARS'
  and (
       a.runtime_allowed = true
    or a.execution_enabled = true
    or t.origin <> 'paper'
    or t.trade_source <> 'paper'
    or t.symbol <> 'GDU6@RTSX'
    or t.strategy <> 'gold_short_only_shadow_v1'
    or t.timeframe <> 'M5'
    or t.side <> 'BUY'
  );
")

echo "unsafe_gold_synthetic_exit_rows=${unsafe_rows}"

if [ "${unsafe_rows}" != "0" ]; then
  echo "FAIL: unsafe synthetic exit rows"
  exit 1
fi

wrong_policy_rows=$(psql "$DATABASE_URL" -At -c "
select count(*)
from gold_synthetic_exit_policy_audit_v1
where exit_policy <> 'TIME_EXIT_M5_12BARS'
  and synthetic_exit_trade_id is not null;
")

echo "wrong_policy_applied_rows=${wrong_policy_rows}"

if [ "${wrong_policy_rows}" != "0" ]; then
  echo "FAIL: non-12bar policy was applied"
  exit 1
fi

echo TEST_GOLD_SYNTHETIC_EXIT_APPLY_V1_OK
