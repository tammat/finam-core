#!/usr/bin/env bash
set -euo pipefail

psql "$DATABASE_URL" -v ON_ERROR_STOP=1 \
  -f scripts/create_runtime_active_universe.sql >/dev/null

psql "$DATABASE_URL" -P pager=off -c "
select column_name, data_type
from information_schema.columns
where table_name = 'runtime_active_universe'
order by ordinal_position;
"

echo "OK: runtime_active_universe table"
