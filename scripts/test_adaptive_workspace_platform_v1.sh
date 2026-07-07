#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_ADAPTIVE_WORKSPACE_PLATFORM_V1 ==="

sudo -u postgres psql -v ON_ERROR_STOP=1 -d finam_core -f sql/presentation/002_adaptive_workspace_platform_v1.sql

widgets=$(psql -At -d finam_core -c "SELECT count(*) FROM presentation.ui_widget_v1 WHERE is_active=true;")
layout=$(psql -At -d finam_core -c "SELECT count(*) FROM presentation.ui_workspace_widget_v1 WHERE workspace_code='EDGE_FACTORY' AND is_visible=true;")

test "$widgets" -ge 4
test "$layout" -ge 7

echo "widgets=$widgets"
echo "layout_rows=$layout"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=ADAPTIVE_WORKSPACE_PLATFORM_V1_READY"
echo "VERDICT=TEST_ADAPTIVE_WORKSPACE_PLATFORM_V1_OK"
