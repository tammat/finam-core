#!/usr/bin/env bash
set -euo pipefail

psql "$DATABASE_URL" -v ON_ERROR_STOP=1 \
  -f scripts/create_grafana_alert_views_ru.sql >/dev/null

psql "$DATABASE_URL" -P pager=off -c "
select *
from v_grafana_alerts_ru
limit 20;
"

echo "OK: Grafana RU alert views"
