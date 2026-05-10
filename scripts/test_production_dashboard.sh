#!/usr/bin/env bash
set -euo pipefail

test -f sql/20260510_production_dashboard_views.sql
test -x scripts/show_production_dashboard.sh

grep -q "v_production_health" sql/20260510_production_dashboard_views.sql
grep -q "v_orders_dashboard" sql/20260510_production_dashboard_views.sql
grep -q "v_positions_dashboard" sql/20260510_production_dashboard_views.sql
grep -q "v_dlq_dashboard" sql/20260510_production_dashboard_views.sql
grep -q "PRODUCTION_DASHBOARD_OK" scripts/show_production_dashboard.sh

echo "PRODUCTION_DASHBOARD_SCRIPT_OK"
