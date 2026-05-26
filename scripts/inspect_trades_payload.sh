#!/usr/bin/env bash
set -euo pipefail

psql "$DATABASE_URL" -c "
select
  id,
  symbol,
  side,
  qty,
  price,
  strategy,
  timeframe,
  trade_source,
  jsonb_pretty(payload) as payload
from trades
order by id desc
limit 3;
"
