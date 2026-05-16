#!/usr/bin/env bash
set -euo pipefail

psql "$DATABASE_URL" -v ON_ERROR_STOP=1 \
  -f scripts/create_grafana_views_ru.sql >/dev/null

psql "$DATABASE_URL" -P pager=off -c "select * from v_grafana_execution_lineage limit 5;"
psql "$DATABASE_URL" -P pager=off -c "select * from v_grafana_adaptive_position_exposure limit 5;"
psql "$DATABASE_URL" -P pager=off -c "select * from v_grafana_institutional_flow_state limit 5;"

echo "OK: Grafana RU views"
