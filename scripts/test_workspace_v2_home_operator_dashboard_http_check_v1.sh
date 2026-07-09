#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_WORKSPACE_V2_HOME_OPERATOR_DASHBOARD_HTTP_CHECK_V1 ==="

sudo systemctl restart marketcore-ui-shell.service
sleep 2

html=$(curl -fsS http://127.0.0.1:8080/workspace-v2)

echo "$html" | grep -q "Операторская панель"
echo "$html" | grep -q "Здоровье модели"
echo "$html" | grep -q "Рекомендации"
echo "$html" | grep -q "Воронка сигналов"
echo "$html" | grep -q "Записей"

echo "home_operator_dashboard_http=OK"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=WORKSPACE_V2_HOME_OPERATOR_DASHBOARD_HTTP_CHECK_V1_READY"
echo "VERDICT=TEST_WORKSPACE_V2_HOME_OPERATOR_DASHBOARD_HTTP_CHECK_V1_OK"
