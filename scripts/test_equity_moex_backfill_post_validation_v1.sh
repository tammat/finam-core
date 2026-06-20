#!/usr/bin/env bash
set -euo pipefail

echo "=== EQUITY_MOEX_BACKFILL_POST_VALIDATION_V1 ==="

symbols="'NVTK@MISX','OZON@MISX','T@MISX','X5@MISX'"

psql "$DATABASE_URL" -c "
select
  symbol,
  timeframe,
  count(*) as bars,
  min(ts) as first_ts,
  max(ts) as last_ts
from market_bars
where symbol in ($symbols)
  and timeframe in ('M1','M5')
group by symbol, timeframe
order by symbol, timeframe;
"

m1_count="$(psql "$DATABASE_URL" -Atc "
select count(*)
from market_bars
where symbol in ($symbols)
  and timeframe='M1';
")"

m5_count="$(psql "$DATABASE_URL" -Atc "
select count(*)
from market_bars
where symbol in ($symbols)
  and timeframe='M5';
")"

runtime_count="$(psql "$DATABASE_URL" -Atc "
select count(*)
from runtime_active_universe
where symbol in ($symbols);
")"

echo "m1_count=$m1_count"
echo "m5_count=$m5_count"
echo "runtime_count=$runtime_count"

if [ "$m1_count" -le 0 ]; then
  echo "VERDICT=EQUITY_MOEX_BACKFILL_M1_NOT_LOADED"
  exit 1
fi

if [ "$runtime_count" -ne 4 ]; then
  echo "VERDICT=EQUITY_MOEX_BACKFILL_RUNTIME_UNIVERSE_INCOMPLETE"
  exit 1
fi

if [ "$m5_count" -eq 0 ]; then
  echo "NOTE=M5_NOT_RETURNED_BY_MOEX_DIRECTLY"
  echo "NEXT_REQUIRED=EQUITY_M1_TO_M5_AGGREGATION_V1"
fi

echo "VERDICT=EQUITY_MOEX_BACKFILL_POST_VALIDATION_OK"
echo "TEST_EQUITY_MOEX_BACKFILL_POST_VALIDATION_V1_OK"
