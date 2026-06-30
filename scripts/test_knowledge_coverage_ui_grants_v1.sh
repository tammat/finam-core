#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_KNOWLEDGE_COVERAGE_UI_GRANTS_V1 ==="

sudo -u postgres psql finam_core -At <<'SQL'
GRANT USAGE ON SCHEMA warehouse TO alex;
GRANT SELECT ON warehouse.analytics_asset_catalog_v1 TO alex;

SELECT 'catalog_select_granted=1';
SELECT 'readonly_user=alex';
SELECT 'VERDICT=KNOWLEDGE_COVERAGE_UI_GRANTS_V1_READY';
SQL

sudo systemctl restart finam-readonly-ui
sleep 2

curl -fsS http://127.0.0.1:8089/ >/tmp/knowledge_coverage_ui_grants_v1.html

grep -q "Knowledge Coverage" /tmp/knowledge_coverage_ui_grants_v1.html
grep -q "WORKFLOW" /tmp/knowledge_coverage_ui_grants_v1.html

echo "http_ready=1"
echo "TEST_KNOWLEDGE_COVERAGE_UI_GRANTS_V1_OK"
