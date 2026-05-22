#!/usr/bin/env bash
set -euo pipefail

grep -q "v_exit_alpha_radar_dashboard" scripts/create_exit_alpha_radar_dashboard_view.sql
grep -q "strategy_exit_alpha_radar" scripts/create_exit_alpha_radar_dashboard_view.sql
grep -q "strategy_best_exit_alpha_policy" scripts/create_exit_alpha_radar_dashboard_view.sql
grep -q "strategy_statistics_v2" scripts/create_exit_alpha_radar_dashboard_view.sql
grep -q "futures_regime_governance" scripts/create_exit_alpha_radar_dashboard_view.sql

echo "TEST_EXIT_ALPHA_RADAR_DASHBOARD_VIEW_OK"
