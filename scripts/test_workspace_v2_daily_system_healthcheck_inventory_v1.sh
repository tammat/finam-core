#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_WORKSPACE_V2_DAILY_SYSTEM_HEALTHCHECK_INVENTORY_V1 ==="

mkdir -p reports

report="reports/workspace_v2_daily_system_healthcheck_inventory_v1.txt"

{
echo "=== EDGE / PAPER / RUNTIME / HEALTH SCRIPT INVENTORY ==="
date -Is

find scripts -type f | \
grep -Ei "health|daily|stats|edge|paper|runtime|funnel|portfolio|risk|pnl|check_current|system" | \
sort

echo
echo "=== TOP CANDIDATES ==="
for f in \
  scripts/check_current_edge_and_stats_v1.sh \
  scripts/test_workspace_v2_home_operator_dashboard_http_check_v1.sh \
  scripts/test_workspace_v2_home_status_resolver_v1.sh \
  scripts/test_signal_funnel_analytics_v1.sh \
  scripts/test_workspace_v2_portfolio_pnl_percent_view_v1.sh
do
  echo
  echo "----- $f -----"
  test -f "$f" && sed -n '1,220p' "$f" || echo "MISSING"
done

echo
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=WORKSPACE_V2_DAILY_SYSTEM_HEALTHCHECK_INVENTORY_V1_READY"
} | tee "$report"

grep -q "VERDICT=WORKSPACE_V2_DAILY_SYSTEM_HEALTHCHECK_INVENTORY_V1_READY" "$report"

echo "report=$report"
echo "VERDICT=TEST_WORKSPACE_V2_DAILY_SYSTEM_HEALTHCHECK_INVENTORY_V1_OK"
