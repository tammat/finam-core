#!/usr/bin/env bash
set -euo pipefail

echo "=== EQUITY_M1_TO_M5_POST_VALIDATION_V1 ==="

symbols="'NVTK@MISX','OZON@MISX','T@MISX','X5@MISX'"

echo "--- MARKET_BARS M5 ---"
psql "$DATABASE_URL" -c "
select
  symbol,
  timeframe,
  count(*) as bars,
  min(ts) as first_ts,
  max(ts) as last_ts
from market_bars
where symbol in ($symbols)
  and timeframe='M5'
group by symbol, timeframe
order by symbol;
"

echo "--- BREAKOUT HISTORY LATEST ---"
psql "$DATABASE_URL" -c "
select distinct on (symbol)
  symbol,
  timeframe,
  created_at,
  bar_ts,
  close,
  prev_high,
  status
from analytics_multi_asset_breakout_row_v1
where symbol in ($symbols)
  and timeframe='M5'
order by symbol, created_at desc;
"

m5_count="$(psql "$DATABASE_URL" -Atc "
select count(*)
from market_bars
where symbol in ($symbols)
  and timeframe='M5';
")"

no_enough_count="$(psql "$DATABASE_URL" -Atc "
select count(*)
from (
  select distinct on (symbol)
    symbol,
    status
  from analytics_multi_asset_breakout_row_v1
  where symbol in ($symbols)
    and timeframe='M5'
  order by symbol, created_at desc
) t
where status like '%NO_ENOUGH_BARS%';
")"

echo "m5_count=$m5_count"
echo "latest_no_enough_bars=$no_enough_count"

if [ "$m5_count" -le 0 ]; then
  echo "VERDICT=EQUITY_M1_TO_M5_POST_VALIDATION_M5_NOT_FOUND"
  exit 1
fi

if [ "$no_enough_count" -gt 0 ]; then
  echo "VERDICT=EQUITY_M5_BARS_EXIST_BUT_WATCHER_STILL_NO_ENOUGH_BARS"
  echo "NEXT_REQUIRED=EQUITY_BREAKOUT_WATCHER_MARKET_BARS_SOURCE_AUDIT_V1"
  exit 0
fi

echo "VERDICT=EQUITY_M1_TO_M5_POST_VALIDATION_OK"
echo "TEST_EQUITY_M1_TO_M5_POST_VALIDATION_V1_OK"
