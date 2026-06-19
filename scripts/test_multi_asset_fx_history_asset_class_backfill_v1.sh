#!/usr/bin/env bash
set -euo pipefail

cd "$(git rev-parse --show-toplevel)"

echo "=== TEST MULTI ASSET FX HISTORY ASSET CLASS BACKFILL V1 ==="
echo "runtime_allow=0"
echo "execution_enabled=0"
echo "real_trading_enabled=0"
echo "orders_create=0"
echo "execution_intents_create=0"

python3 -m py_compile src/scripts/research/backfill_multi_asset_fx_history_asset_class_v1.py

PYTHONPATH=src \
RUNTIME_ALLOW_TRADING=0 EXECUTION_ENABLED=0 REAL_TRADING_ENABLED=0 \
APPLY_FIX=0 \
python3 src/scripts/research/backfill_multi_asset_fx_history_asset_class_v1.py \
  | tee /tmp/fx_history_asset_class_backfill_plan_v1.log

grep -q "MULTI_ASSET_FX_HISTORY_ASSET_CLASS_BACKFILL_V1_OK" /tmp/fx_history_asset_class_backfill_plan_v1.log
grep -q "VERDICT=" /tmp/fx_history_asset_class_backfill_plan_v1.log
grep -q "orders_create=0" /tmp/fx_history_asset_class_backfill_plan_v1.log
grep -q "execution_intents_create=0" /tmp/fx_history_asset_class_backfill_plan_v1.log

PYTHONPATH=src \
RUNTIME_ALLOW_TRADING=0 EXECUTION_ENABLED=0 REAL_TRADING_ENABLED=0 \
APPLY_FIX=1 \
python3 src/scripts/research/backfill_multi_asset_fx_history_asset_class_v1.py \
  | tee /tmp/fx_history_asset_class_backfill_apply_v1.log

grep -q "VERDICT=FX_HISTORY_ASSET_CLASS_BACKFILL_APPLIED" /tmp/fx_history_asset_class_backfill_apply_v1.log
grep -q "MULTI_ASSET_FX_HISTORY_ASSET_CLASS_BACKFILL_V1_OK" /tmp/fx_history_asset_class_backfill_apply_v1.log

if psql "$DATABASE_URL" -At -c "
select count(*)
from analytics_multi_asset_breakout_row_v1
where symbol in ('USDRUBF@RTSX','CNYRUBF@RTSX','CNYRUB_TOM@MISX')
  and asset_class not in ('FX_FUTURES','FX_SPOT');
" | grep -v '^0$'; then
  echo "ERROR: wrong FX asset_class remains"
  exit 1
fi

echo "=== FX HISTORY AFTER BACKFILL ==="
psql "$DATABASE_URL" -c "
select
  symbol,
  asset_class,
  timeframe,
  role,
  count(*) as observations,
  count(*) filter (where status like '%BREAKOUT_READY%') as ready_count,
  max(created_at) as last_seen
from analytics_multi_asset_breakout_row_v1
where symbol in ('USDRUBF@RTSX','CNYRUBF@RTSX','CNYRUB_TOM@MISX')
group by symbol, asset_class, timeframe, role
order by symbol, asset_class, timeframe, role;
"

echo "VERDICT=MULTI_ASSET_FX_HISTORY_ASSET_CLASS_BACKFILL_OK"
echo TEST_MULTI_ASSET_FX_HISTORY_ASSET_CLASS_BACKFILL_V1_OK
