#!/usr/bin/env bash
set -euo pipefail

cd "$(git rev-parse --show-toplevel)"
export PYTHONPATH=src

python3 -m py_compile src/scripts/research/build_gold_synthetic_exit_policy_audit_v1.py

python3 src/scripts/research/build_gold_synthetic_exit_policy_audit_v1.py \
  | tee /tmp/gold_synthetic_exit_policy_audit_v1.log

grep -q "GOLD_SYNTHETIC_EXIT_POLICY_AUDIT_V1_OK" /tmp/gold_synthetic_exit_policy_audit_v1.log
grep -q "TIME_EXIT_M5_3BARS" /tmp/gold_synthetic_exit_policy_audit_v1.log
grep -q "TIME_EXIT_M5_6BARS" /tmp/gold_synthetic_exit_policy_audit_v1.log
grep -q "TIME_EXIT_M5_12BARS" /tmp/gold_synthetic_exit_policy_audit_v1.log

unsafe_rows=$(psql "$DATABASE_URL" -At -c "
select count(*)
from gold_synthetic_exit_policy_audit_v1
where runtime_allowed = true
   or execution_enabled = true
   or symbol <> 'GDU6@RTSX'
   or strategy <> 'gold_short_only_shadow_v1'
   or timeframe <> 'M5'
   or entry_side <> 'SELL'
   or synthetic_exit_side <> 'BUY';
")

echo "unsafe_gold_exit_policy_rows=${unsafe_rows}"

if [ "${unsafe_rows}" != "0" ]; then
  echo "FAIL: unsafe gold exit policy rows"
  exit 1
fi

echo TEST_GOLD_SYNTHETIC_EXIT_POLICY_AUDIT_V1_OK
