#!/usr/bin/env bash
set -euo pipefail

cd "$(git rev-parse --show-toplevel)"

echo "=== TEST NGQ6 M1 TRADE IDENTITY FIX V1 ==="

python3 -m py_compile src/scripts/research/apply_ngq6_m1_trade_identity_fix_v1.py

python3 src/scripts/research/apply_ngq6_m1_trade_identity_fix_v1.py \
  | tee /tmp/ngq6_m1_trade_identity_fix_v1.log

grep -q "NGQ6_M1_TRADE_IDENTITY_FIX_V1_OK" /tmp/ngq6_m1_trade_identity_fix_v1.log
grep -q "runtime_allow=0" /tmp/ngq6_m1_trade_identity_fix_v1.log
grep -q "execution_enabled=0" /tmp/ngq6_m1_trade_identity_fix_v1.log
grep -q "ngq6_bad_identity_trades=0" /tmp/ngq6_m1_trade_identity_fix_v1.log

bad_rows=$(psql "$DATABASE_URL" -At -c "
select count(*)
from trades
where symbol='NGQ6@RTSX'
  and coalesce(trade_source,'')='paper'
  and coalesce(origin,'paper')='paper'
  and (
       coalesce(strategy,'') in ('', 'UNKNOWN', 'UNKNOWN_STRATEGY')
    or coalesce(timeframe,'') in ('', 'LIVE', 'UNKNOWN', 'UNKNOWN_TIMEFRAME')
  );
")

echo "bad_ngq6_identity_rows=${bad_rows}"

if [ "${bad_rows}" != "0" ]; then
  echo "FAIL: NGQ6 bad identity rows remain"
  exit 1
fi

psql "$DATABASE_URL" -c "
select
    id,
    created_at,
    symbol,
    strategy,
    timeframe,
    side,
    origin,
    trade_source,
    qty,
    price
from trades
where symbol='NGQ6@RTSX'
order by created_at desc
limit 10;
"

echo TEST_NGQ6_M1_TRADE_IDENTITY_FIX_V1_OK
