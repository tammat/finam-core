#!/usr/bin/env bash
set -euo pipefail

SYMBOL="${SYMBOL:-BRM6@RTSX}"
TRADE_SOURCE="${TRADE_SOURCE:-paper}"

psql "$DATABASE_URL" -c "
with x as (
  select
    id,
    symbol,
    side,
    qty,
    price,
    trade_source,
    strategy,
    timeframe,
    ts,
    lag(id) over(order by ts, id) as prev_id,
    lag(ts) over(order by ts, id) as prev_ts
  from trades
  where is_invalid = false
    and symbol = '$SYMBOL'
    and trade_source = '$TRADE_SOURCE'
)
select
  id,
  prev_id,
  id - prev_id as id_gap,
  ts,
  prev_ts,
  ts - prev_ts as ts_gap,
  side,
  qty,
  price,
  strategy,
  timeframe
from x
where prev_id is not null
  and (
    id - prev_id > 100
    or ts - prev_ts > interval '30 minutes'
  )
order by ts, id;
"
