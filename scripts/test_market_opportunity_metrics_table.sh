#!/usr/bin/env bash
set -euo pipefail

psql "$DATABASE_URL" -v ON_ERROR_STOP=1 \
  -f scripts/create_market_opportunity_metrics.sql >/dev/null

psql "$DATABASE_URL" -v ON_ERROR_STOP=1 -P pager=off -c "
insert into market_opportunity_metrics (
  symbol, asset_class, atr_pct, rvol, turnover, spread_pct, regime, is_tradeable, raw
)
values (
  'OZON@MISX',
  'EQUITY',
  0.015,
  2.1,
  2000000000,
  0.001,
  'trend_up_high_vol',
  true,
  '{\"test\": true}'::jsonb
);
"

psql "$DATABASE_URL" -P pager=off -c "
select symbol, asset_class, atr_pct, rvol, turnover, spread_pct, regime, is_tradeable
from market_opportunity_metrics
where symbol='OZON@MISX'
order by calculated_at desc
limit 1;
"

echo "OK: market_opportunity_metrics table"
