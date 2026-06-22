#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_DASHBOARD_TRAFFIC_LIGHT_INDICATORS_V1 ==="

html="$(curl -fsS http://127.0.0.1:8088/mobile)"


echo "$html" | grep -q "Главный кандидат"
echo "$html" | grep -q "сбор статистики"

echo "VERDICT=DASHBOARD_TRAFFIC_LIGHT_INDICATORS_OK"
echo "TEST_DASHBOARD_TRAFFIC_LIGHT_INDICATORS_V1_OK"
