#!/usr/bin/env bash
set -euo pipefail

cd "$(git rev-parse --show-toplevel)"
export PYTHONPATH=src

python3 -m py_compile src/scripts/research/apply_trade_identity_backfill_v1.py

python3 src/scripts/research/apply_trade_identity_backfill_v1.py \
  | tee /tmp/trade_identity_backfill_v1.log

grep -q "TRADE_IDENTITY_BACKFILL_V1_OK" /tmp/trade_identity_backfill_v1.log

remaining_missing=$(psql "$DATABASE_URL" -At -c "
select count(*)
from trades
where origin='paper'
  and trade_source='paper'
  and symbol in ('BRN6@RTSX', 'NGN6@RTSX')
  and coalesce(strategy, '') = ''
  and coalesce(timeframe, '') = '';
")

echo "remaining_missing_identity=${remaining_missing}"

if [ "${remaining_missing}" != "0" ]; then
  echo "FAIL: remaining missing identity rows exist"
  exit 1
fi

unexpected_updated=$(psql "$DATABASE_URL" -At -c "
select count(*)
from trade_identity_backfill_audit_v1
where symbol not in ('BRN6@RTSX', 'NGN6@RTSX')
   or new_timeframe <> 'M5'
   or new_strategy not in ('BR_CONSERVATIVE_BREAKOUT', 'NG_CONSERVATIVE_BREAKOUT');
")

echo "unexpected_updated_rows=${unexpected_updated}"

if [ "${unexpected_updated}" != "0" ]; then
  echo "FAIL: unexpected audit rows"
  exit 1
fi

echo TEST_TRADE_IDENTITY_BACKFILL_V1_OK
