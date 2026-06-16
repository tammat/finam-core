#!/usr/bin/env bash
set -euo pipefail

cd "$(git rev-parse --show-toplevel)"

psql "$DATABASE_URL" -v ON_ERROR_STOP=1 -c "
select
    origin,
    strategy,
    timeframe,
    is_invalid,
    invalid_reason,
    count(*) rows
from trades
where symbol='USDRUBF@RTSX'
group by origin, strategy, timeframe, is_invalid, invalid_reason
order by rows desc;
"

psql "$DATABASE_URL" -v ON_ERROR_STOP=1 -c "
select count(*) unsafe_rows
from trades
where symbol='USDRUBF@RTSX'
  and origin='backfill_from_fills'
  and coalesce(strategy,'')=''
  and coalesce(timeframe,'')=''
  and is_invalid=false;
"

echo TEST_USDRUB_BACKFILL_QUARANTINE_V1_OK
