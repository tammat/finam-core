#!/usr/bin/env bash
set -euo pipefail

cd "$(git rev-parse --show-toplevel)"
export PYTHONPATH=src

python3 -m py_compile src/scripts/research/build_trade_identity_backfill_audit_v1.py

python3 src/scripts/research/build_trade_identity_backfill_audit_v1.py \
  | tee /tmp/trade_identity_backfill_audit_v1.log

grep -q "TRADE_IDENTITY_BACKFILL_AUDIT_V1_OK" /tmp/trade_identity_backfill_audit_v1.log

unsafe_rows=$(psql "$DATABASE_URL" -At -c "
select count(*)
from trade_identity_backfill_audit_v1
where runtime_allowed = true
   or execution_enabled = true;
")

echo "unsafe_backfill_audit_rows=${unsafe_rows}"

if [ "${unsafe_rows}" != "0" ]; then
  echo "FAIL: audit enabled runtime/execution"
  exit 1
fi

unexpected_rows=$(psql "$DATABASE_URL" -At -c "
select count(*)
from trade_identity_backfill_audit_v1
where symbol not in ('BRN6@RTSX', 'NGN6@RTSX')
   or origin <> 'paper'
   or trade_source <> 'paper'
   or new_timeframe <> 'M5'
   or new_strategy not in ('BR_CONSERVATIVE_BREAKOUT', 'NG_CONSERVATIVE_BREAKOUT');
")

echo "unexpected_backfill_audit_rows=${unexpected_rows}"

if [ "${unexpected_rows}" != "0" ]; then
  echo "FAIL: audit contains non-whitelisted rows"
  exit 1
fi

echo TEST_TRADE_IDENTITY_BACKFILL_AUDIT_V1_OK
