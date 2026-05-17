#!/usr/bin/env bash
set -euo pipefail

psql "$DATABASE_URL" -v ON_ERROR_STOP=1 \
  -f scripts/dedup_market_event_calendar.sql >/dev/null

psql "$DATABASE_URL" -v ON_ERROR_STOP=1 \
  -f scripts/add_market_event_calendar_unique_key.sql >/dev/null

psql "$DATABASE_URL" -P pager=off -c "
select
    event_time,
    event_type,
    instrument_group,
    event_name,
    count(*) as cnt
from market_event_calendar
group by 1,2,3,4
having count(*) > 1;
"

echo "OK: market_event_calendar unique key"
