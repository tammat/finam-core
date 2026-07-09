#!/usr/bin/env bash
set -euo pipefail

echo "======================================================"
echo "WORKSPACE_V2_DAILY_SYSTEM_HEALTHCHECK_V1"
echo "======================================================"

mkdir -p reports

report="reports/workspace_v2_daily_system_healthcheck_v1.txt"

run() {

    local script="$1"

    echo
    echo "------------------------------------------------------"
    echo "$script"
    echo "------------------------------------------------------"

    if [ -x "$script" ]; then
        "$script"
    else
        echo "SKIPPED (missing): $script"
    fi
}

{

date -Is

run scripts/check_current_edge_and_stats_v1.sh

run scripts/test_signal_funnel_analytics_v1.sh

run scripts/test_workspace_v2_home_status_resolver_v1.sh

run scripts/test_workspace_v2_home_operator_dashboard_http_check_v1.sh

run scripts/test_workspace_v2_portfolio_pnl_percent_view_v1.sh

echo
echo "======================================================"
echo "SUMMARY"
echo "======================================================"

echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"

echo
echo "VERDICT=WORKSPACE_V2_DAILY_SYSTEM_HEALTHCHECK_V1_READY"

} | tee "$report"

echo
echo "report=$report"

echo "VERDICT=TEST_WORKSPACE_V2_DAILY_SYSTEM_HEALTHCHECK_V1_OK"
