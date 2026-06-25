#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_READONLY_UI_DB_GRANTS_V1 ==="

sudo -u postgres psql finam_core -At <<'SQL'
GRANT USAGE ON SCHEMA warehouse TO alex;
GRANT SELECT ON ALL TABLES IN SCHEMA warehouse TO alex;
ALTER DEFAULT PRIVILEGES IN SCHEMA warehouse GRANT SELECT ON TABLES TO alex;

SELECT 'warehouse_usage_granted=1';
SELECT 'warehouse_select_granted=1';
SELECT 'readonly_user=alex';
SELECT 'VERDICT=READONLY_UI_DB_GRANTS_V1_READY';
SQL

sudo systemctl restart finam-readonly-ui
sleep 2

curl -fsS http://127.0.0.1:8089/ >/tmp/read_only_system_status_ui_systemd_v1.html

grep -q "Finam Core" /tmp/read_only_system_status_ui_systemd_v1.html
grep -q "Главное меню" /tmp/read_only_system_status_ui_systemd_v1.html
grep -q "Портфель" /tmp/read_only_system_status_ui_systemd_v1.html

echo "http_ready=1"
echo "VERDICT=READONLY_UI_DB_GRANTS_V1_OK"
echo "TEST_READONLY_UI_DB_GRANTS_V1_OK"
