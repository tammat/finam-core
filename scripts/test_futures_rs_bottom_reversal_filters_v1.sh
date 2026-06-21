#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_FUTURES_RS_BOTTOM_REVERSAL_FILTERS_V1 ==="

out="$(mktemp)"

python3 -m py_compile src/scripts/research/build_futures_rs_bottom_reversal_filters_v1.py

PYTHONPATH=src \
RUNTIME_ALLOW_TRADING=0 \
EXECUTION_ENABLED=0 \
REAL_TRADING_ENABLED=0 \
python3 src/scripts/research/build_futures_rs_bottom_reversal_filters_v1.py \
  --migrate --save | tee "$out"

grep -q "VERDICT=FUTURES_RS_BOTTOM_REVERSAL_FILTERS_READY" "$out"
grep -q "TEST_FUTURES_RS_BOTTOM_REVERSAL_FILTERS_V1_OK" "$out"
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
order by profit_factor desc nulls last, observations desc
limit 30;
"

echo "VERDICT=FUTURES_RS_BOTTOM_REVERSAL_FILTERS_TEST_OK"
echo "TEST_FUTURES_RS_BOTTOM_REVERSAL_FILTERS_V1_OK"
