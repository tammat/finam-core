#!/usr/bin/env bash
set -euo pipefail

psql "$DATABASE_URL" -v ON_ERROR_STOP=1 \
  -f scripts/create_closed_trade_analytics_views.sql >/dev/null

psql "$DATABASE_URL" -P pager=off -c "
select
    analytics_symbol,
    strategy,
    count(*) as closed_trades,
    round(sum(net_pnl)::numeric, 6) as total_pnl,
    round(avg(return_pct)::numeric, 6) as avg_return,
    round(avg(is_win)::numeric, 4) as winrate
from analytics_closed_trades_normalized
group by analytics_symbol, strategy
order by total_pnl desc
limit 20;
"

echo "OK: analytics_closed_trades_normalized"
