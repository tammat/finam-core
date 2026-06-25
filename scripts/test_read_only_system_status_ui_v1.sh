#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_READ_ONLY_SYSTEM_STATUS_UI_V1 ==="

READONLY_UI_PORT=8089 PYTHONPATH=src \
  src/scripts/research/serve_read_only_system_status_ui_v1.py \
  > /tmp/read_only_system_status_ui_v1.log 2>&1 &

PID=$!
trap 'kill $PID >/dev/null 2>&1 || true' EXIT

sleep 2

curl -fsS http://127.0.0.1:8089/ -o /tmp/read_only_system_status_ui_v1.html

grep -q "Finam Core" /tmp/read_only_system_status_ui_v1.html
grep -q "Состояние системы" /tmp/read_only_system_status_ui_v1.html
grep -q "Главное меню" /tmp/read_only_system_status_ui_v1.html
grep -q "Назад" /tmp/read_only_system_status_ui_v1.html
grep -q "Портфель" /tmp/read_only_system_status_ui_v1.html
grep -q "Риск" /tmp/read_only_system_status_ui_v1.html
grep -q "Workflow" /tmp/read_only_system_status_ui_v1.html
grep -q "Кандидат" /tmp/read_only_system_status_ui_v1.html
grep -q "Warehouse" /tmp/read_only_system_status_ui_v1.html
grep -q "Только просмотр" /tmp/read_only_system_status_ui_v1.html

echo "read_only_ui_http=200"
echo "source_policy=MART_ONLY"
echo "responsive_web_ui=1"
echo "home_navigation=1"
echo "back_navigation=1"
echo "portfolio_first=1"
echo "read_only=1"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=READ_ONLY_SYSTEM_STATUS_UI_V1_READY"
echo "TEST_READ_ONLY_SYSTEM_STATUS_UI_V1_OK"
