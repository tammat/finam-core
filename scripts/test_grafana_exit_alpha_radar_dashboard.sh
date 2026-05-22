#!/usr/bin/env bash
set -euo pipefail

test -f infra/grafana/dashboards/exit_alpha_radar_dashboard.json
grep -q "v_exit_alpha_radar_dashboard" infra/grafana/dashboards/exit_alpha_radar_dashboard.json
grep -q "Exit Alpha Radar" infra/grafana/dashboards/exit_alpha_radar_dashboard.json
grep -q "exit_alpha_pf" infra/grafana/dashboards/exit_alpha_radar_dashboard.json

echo "TEST_GRAFANA_EXIT_ALPHA_RADAR_DASHBOARD_OK"
