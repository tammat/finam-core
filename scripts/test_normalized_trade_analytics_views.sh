#!/usr/bin/env bash
set -euo pipefail

psql "$DATABASE_URL" -v ON_ERROR_STOP=1 -P pager=off -c "
select
  analytics_symbol,
  strategy,
  count(*) as trades,
  round(sum(signed_cashflow)::numeric, 4) as signed_cashflow,
  round(avg(commission_pct)::numeric, 8) as avg_commission_pct
from analytics_trades_normalized
where strategy is not null
group by analytics_symbol, strategy
order by trades desc
limit 20;
"

psql "$DATABASE_URL" -v ON_ERROR_STOP=1 -P pager=off -c "
select ts_msk, execution_symbol, analytics_symbol, side, qty, price, notional, signed_cashflow
from analytics_trades_normalized
order by ts desc
limit 10;
"
