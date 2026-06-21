#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_FUTURES_RS_BOTTOM_REVERSAL_FILTERS_FIX_V1_1 ==="

out="$(mktemp)"

python3 -m py_compile src/scripts/research/build_futures_rs_bottom_reversal_filters_fix_v1_1.py

PYTHONPATH=src \
RUNTIME_ALLOW_TRADING=0 \
EXECUTION_ENABLED=0 \
REAL_TRADING_ENABLED=0 \
python3 src/scripts/research/build_futures_rs_bottom_reversal_filters_fix_v1_1.py \
  --migrate --save | tee "$out"

grep -q "VERDICT=FUTURES_RS_BOTTOM_REVERSAL_FILTERS_FIX_V1_1_READY" "$out"
grep -q "TEST_FUTURES_RS_BOTTOM_REVERSAL_FILTERS_FIX_V1_1_OK" "$out"
grep -q "db_update=1" "$out"
grep -q "runtime_changed=0" "$out"
grep -q "execution_changed=0" "$out"
grep -q "telegram_send=0" "$out"
grep -q "FUTURES_RS_BOTTOM_FILTER_ROW" "$out"

psql "$DATABASE_URL" -c "
select
  selection,
  filter_name,
  horizon_min,
  observations,
  wins,
  losses,
  round(winrate, 4) as winrate,
  round(avg_return_pct, 6) as avg_return_pct,
  round(profit_factor, 4) as profit_factor
from analytics_futures_rs_bottom_reversal_filters_v1
where selection in ('BOTTOM1','BOTTOM3')
order by profit_factor desc nulls last, observations desc
limit 30;
"

psql "$DATABASE_URL" -At -c "
select
  case
    when avg_return_pct > 0 and profit_factor > 1
    then 'BOTTOM1_ALL_240_SIGN_FIXED'
    else 'BOTTOM1_ALL_240_SIGN_STILL_BAD'
  end
from analytics_futures_rs_bottom_reversal_filters_v1
where selection='BOTTOM1'
  and filter_name='ALL'
  and horizon_min=240;
" | grep -q "BOTTOM1_ALL_240_SIGN_FIXED"

psql "$DATABASE_URL" -At -c "
select
  case
    when avg_return_pct > 0 and profit_factor > 1
    then 'BOTTOM3_ALL_240_SIGN_FIXED'
    else 'BOTTOM3_ALL_240_SIGN_STILL_BAD'
  end
from analytics_futures_rs_bottom_reversal_filters_v1
where selection='BOTTOM3'
  and filter_name='ALL'
  and horizon_min=240;
" | grep -q "BOTTOM3_ALL_240_SIGN_FIXED"

echo "VERDICT=FUTURES_RS_BOTTOM_REVERSAL_FILTERS_FIX_V1_1_TEST_OK"
echo "TEST_FUTURES_RS_BOTTOM_REVERSAL_FILTERS_FIX_V1_1_OK"
