#!/usr/bin/env bash
set -euo pipefail

psql "$DATABASE_URL" -v ON_ERROR_STOP=1 -P pager=off -c "
select analytics_symbol, execution_symbol, strategy, side, qty, price
from analytics_trades_continuous
where execution_symbol='BRN6@RTSX'
order by ts desc
limit 5;
"

psql "$DATABASE_URL" -v ON_ERROR_STOP=1 -P pager=off -c "
select analytics_symbol, strategy, trades, raw_cashflow
from analytics_strategy_expectancy_continuous
order by trades desc
limit 20;
"
