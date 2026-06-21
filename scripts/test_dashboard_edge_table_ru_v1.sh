#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_DASHBOARD_EDGE_TABLE_RU_V1 ==="

sudo systemctl restart finam-multi-asset-breakout-dashboard.service
sleep 5

html="$(curl -fsS http://127.0.0.1:8088/edge)"

echo "$html" | grep -q "Технический рейтинг готовности"
echo "$html" | grep -q "не подтверждённый торговый edge"
echo "$html" | grep -q "Инструмент"
echo "$html" | grep -q "SBER@MISX"

echo "VERDICT=DASHBOARD_EDGE_TABLE_RU_OK"
echo "TEST_DASHBOARD_EDGE_TABLE_RU_V1_OK"
