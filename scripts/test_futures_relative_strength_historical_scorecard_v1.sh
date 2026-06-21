#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_FUTURES_RELATIVE_STRENGTH_HISTORICAL_SCORECARD_V1 ==="

out="$(mktemp)"

python3 -m py_compile src/scripts/research/build_futures_relative_strength_historical_scorecard_v1.py

PYTHONPATH=src \
RUNTIME_ALLOW_TRADING=0 \
EXECUTION_ENABLED=0 \
REAL_TRADING_ENABLED=0 \
python3 src/scripts/research/build_futures_relative_strength_historical_scorecard_v1.py \
  --migrate --save | tee "$out"

grep -q "VERDICT=FUTURES_RELATIVE_STRENGTH_HISTORICAL_SCORECARD_READY" "$out"
grep -q "TEST_FUTURES_RELATIVE_STRENGTH_HISTORICAL_SCORECARD_V1_OK" "$out"
grep -q "db_update=1" "$out"
grep -q "runtime_changed=0" "$out"
grep -q "execution_changed=0" "$out"
grep -q "telegram_send=0" "$out"
grep -q "FUTURES_RS_HIST_ROW" "$out"

psql "$DATABASE_URL" -c "
select
  selection,
  horizon_min,
  observations,
  wins,
  losses,
  round(winrate, 4) as winrate,
  round(avg_return_pct, 6) as avg_return_pct,
  round(profit_factor, 4) as profit_factor
from analytics_futures_rs_historical_scorecard_v1
order by selection, horizon_min;
"

echo "VERDICT=FUTURES_RELATIVE_STRENGTH_HISTORICAL_SCORECARD_TEST_OK"
echo "TEST_FUTURES_RELATIVE_STRENGTH_HISTORICAL_SCORECARD_V1_OK"
