#!/usr/bin/env bash
set -euo pipefail

psql "$DATABASE_URL" -v ON_ERROR_STOP=1 \
  -f scripts/create_strategy_performance_monitor_v2.sql >/dev/null

psql "$DATABASE_URL" -P pager=off -c "
select
  analytics_symbol,
  strategy,
  closed_trades,
  total_net_pnl,
  expectancy,
  winrate,
  profit_factor,
  worst_trade,
  best_trade
from analytics_strategy_performance_monitor_v2
order by total_net_pnl desc;
"

echo "OK: analytics_strategy_performance_monitor_v2"
