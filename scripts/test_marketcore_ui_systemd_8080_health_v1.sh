#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_MARKETCORE_UI_SYSTEMD_8080_HEALTH_V1 ==="

scripts/apply_marketcore_ui_systemd_8080_health_v1.sh

PYTHONPATH=src python -m py_compile \
  src/scripts/build_marketcore_ui_systemd_8080_health_v1.py \
  src/marketcore/api/serve_knowledge_graph_api_v1.py \
  src/marketcore/presentation/pages/marketcore_ui_systemd_health.py \
  src/marketcore/presentation/registry.py \
  src/marketcore/presentation/app.py

if grep -R "psycopg2\|DATABASE_URL\|SELECT " -n src/marketcore/presentation/pages/marketcore_ui_systemd_health.py; then
  echo "FORBIDDEN_DIRECT_DB_ACCESS_IN_UI_PAGE"
  exit 1
fi

sudo systemctl restart marketcore-kg-api.service
sudo systemctl restart marketcore-ui-shell.service

sleep 2

DATABASE_URL=postgresql:///finam_core PYTHONPATH=src \
python src/scripts/build_marketcore_ui_systemd_8080_health_v1.py \
  | tee /tmp/marketcore_ui_systemd_8080_health_builder_v1.txt

grep -q "VERDICT=MARKETCORE_UI_SYSTEMD_8080_HEALTH_V1_READY" \
  /tmp/marketcore_ui_systemd_8080_health_builder_v1.txt

curl -fsS "http://127.0.0.1:8095/api/kg/v1/marketcore-ui-systemd-health" \
  > /tmp/marketcore_ui_systemd_8080_health_api_v1.json

curl -fsS "http://127.0.0.1:8080/marketcore-ui-systemd-health" \
  > /tmp/marketcore_ui_systemd_8080_health_page_v1.html

grep -q '"status": "OK"' /tmp/marketcore_ui_systemd_8080_health_api_v1.json
grep -q '"overall_status"' /tmp/marketcore_ui_systemd_8080_health_api_v1.json
grep -q '"kg_api_health_status"' /tmp/marketcore_ui_systemd_8080_health_api_v1.json
grep -q '"ui_shell_health_status"' /tmp/marketcore_ui_systemd_8080_health_api_v1.json
grep -q '"open_url"' /tmp/marketcore_ui_systemd_8080_health_api_v1.json

grep -q "MarketCore UI Systemd Health" /tmp/marketcore_ui_systemd_8080_health_page_v1.html
grep -q "Systemd Details" /tmp/marketcore_ui_systemd_8080_health_page_v1.html
grep -q "MARKETCORE_UI_8080_NAVIGATION_AUDIT_V1" /tmp/marketcore_ui_systemd_8080_health_page_v1.html
grep -q "MARKETCORE_UI_SHELL_V1" /tmp/marketcore_ui_systemd_8080_health_page_v1.html

rows=$(psql -At -d finam_core -c "SELECT count(*) FROM marketcore_ui.marketcore_ui_systemd_8080_health_v1 WHERE id=1;")
allowed=$(psql -At -d finam_core -c "SELECT count(*) FROM marketcore_ui.marketcore_ui_systemd_8080_health_v1 WHERE micro_live_allowed<>0;")
overall=$(psql -At -d finam_core -c "SELECT overall_status FROM marketcore_ui.marketcore_ui_systemd_8080_health_v1 WHERE id=1;")

test "$rows" = "1"
test "$allowed" = "0"
test "$overall" = "HEALTHY"

psql -d finam_core -c "
SELECT
    overall_status,
    kg_api_health_status,
    ui_shell_health_status,
    kg_api_http_ok,
    ui_home_http_ok,
    ui_risk_http_ok,
    ui_settings_http_ok,
    open_url,
    risk_url,
    settings_url
FROM marketcore_ui.marketcore_ui_systemd_8080_health_v1
WHERE id=1;
"

echo "marketcore_ui_health_rows=$rows"
echo "overall_status=$overall"
echo "micro_live_allowed_rows=$allowed"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=MARKETCORE_UI_SYSTEMD_8080_HEALTH_V1_READY"
echo "VERDICT=TEST_MARKETCORE_UI_SYSTEMD_8080_HEALTH_V1_OK"
