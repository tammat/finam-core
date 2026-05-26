#!/usr/bin/env bash
set -euo pipefail

psql "$DATABASE_URL" -c "
select
  symbol,
  trade_source,
  strategy,
  timeframe,
  is_invalid,
  count(*) as trades,
  min(id) as min_id,
  max(id) as max_id,
  min(ts) as min_ts,
  max(ts) as max_ts
from trades
where symbol = 'BRM6@RTSX'
group by symbol, trade_source, strategy, timeframe, is_invalid
order by trades desc;
"
