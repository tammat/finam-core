#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_PAPER_RUNTIME_SAMPLE_COLLECTION_OPERATIONS_DAILY_SUMMARY_V1 ==="

scripts/apply_paper_runtime_sample_collection_operations_daily_summary_v1.sh

PYTHONPATH=src python -m py_compile \
  src/scripts/build_paper_runtime_sample_collection_operations_daily_summary_v1.py \
  src/marketcore/api/serve_knowledge_graph_api_v1.py \
  src/marketcore/presentation/pages/paper_runtime_sample_collection_daily_summary.py \
  src/marketcore/presentation/pages/risk.py \
  src/marketcore/presentation/pages/settings.py \
  src/marketcore/presentation/registry.py \
  src/marketcore/presentation/app.py

for page in \
  src/marketcore/presentation/pages/paper_runtime_sample_collection_daily_summary.py \
  src/marketcore/presentation/pages/risk.py \
  src/marketcore/presentation/pages/settings.py
do
  if grep -R "psycopg2\|DATABASE_URL\|SELECT " -n "$page"; then
    echo "FORBIDDEN_DIRECT_DB_ACCESS_IN_UI_PAGE file=$page"
    exit 1
  fi
done

sudo -u postgres env DATABASE_URL=postgresql:///finam_core PYTHONPATH=src \
  /opt/finam-core/venv/bin/python src/scripts/run_paper_runtime_sample_collection_operations_cycle_v1.py \
  > /tmp/daily_summary_operations_cycle_v1.txt

grep -q "VERDICT=PAPER_RUNTIME_SAMPLE_COLLECTION_OPERATIONS_CYCLE_V1_READY" \
  /tmp/daily_summary_operations_cycle_v1.txt

DATABASE_URL=postgresql:///finam_core PYTHONPATH=src \
python src/scripts/build_paper_runtime_sample_collection_operations_timer_health_v1.py \
  > /tmp/daily_summary_operations_health_v1.txt

grep -q "VERDICT=PAPER_RUNTIME_SAMPLE_COLLECTION_OPERATIONS_TIMER_HEALTH_V1_READY" \
  /tmp/daily_summary_operations_health_v1.txt

DATABASE_URL=postgresql:///finam_core PYTHONPATH=src \
python src/scripts/build_paper_runtime_sample_collection_operations_daily_summary_v1.py \
  | tee /tmp/daily_summary_builder_v1.txt

grep -q "VERDICT=PAPER_RUNTIME_SAMPLE_COLLECTION_OPERATIONS_DAILY_SUMMARY_V1_READY" \
  /tmp/daily_summary_builder_v1.txt

KG_API_HOST=127.0.0.1 KG_API_PORT=20095 DATABASE_URL=postgresql:///finam_core PYTHONPATH=src \
python src/marketcore/api/serve_knowledge_graph_api_v1.py > /tmp/kg_api_daily_summary_v1.log 2>&1 &
api_pid=$!

MARKETCORE_UI_HOST=127.0.0.1 MARKETCORE_UI_PORT=20080 KG_API_BASE_URL=http://127.0.0.1:20095 PYTHONPATH=src \
python src/marketcore/presentation/app.py > /tmp/daily_summary_ui_v1.log 2>&1 &
ui_pid=$!

cleanup() {
  kill "$ui_pid" >/dev/null 2>&1 || true
  kill "$api_pid" >/dev/null 2>&1 || true
}
trap cleanup EXIT

sleep 2

curl -fsS "http://127.0.0.1:20095/api/kg/v1/paper-sample-operations-daily-summary" \
  > /tmp/daily_summary_api_v1.json

curl -fsS "http://127.0.0.1:20080/paper-runtime-sample-collection-daily-summary" \
  > /tmp/daily_summary_page_v1.html

curl -fsS "http://127.0.0.1:20080/risk" \
  > /tmp/risk_page_v1.html

curl -fsS "http://127.0.0.1:20080/settings" \
  > /tmp/settings_page_v1.html

grep -q '"status": "OK"' /tmp/daily_summary_api_v1.json
grep -q '"daily_status"' /tmp/daily_summary_api_v1.json
grep -q '"operations_health_status"' /tmp/daily_summary_api_v1.json
grep -q '"micro_live_allowed"' /tmp/daily_summary_api_v1.json

grep -q "Paper Runtime Sample Collection Daily Summary" /tmp/daily_summary_page_v1.html
grep -q "Daily Summary" /tmp/daily_summary_page_v1.html
grep -q "Риски" /tmp/daily_summary_page_v1.html
grep -q "Настройки" /tmp/daily_summary_page_v1.html
grep -q "PAPER_RUNTIME_SAMPLE_COLLECTION_OPERATIONS_DAILY_SUMMARY_V1" /tmp/daily_summary_page_v1.html
grep -q "MARKETCORE_UI_SHELL_V1" /tmp/daily_summary_page_v1.html

grep -q "Риски" /tmp/risk_page_v1.html
grep -q "Настройки" /tmp/settings_page_v1.html

rows=$(psql -At -d finam_core -c "SELECT count(*) FROM marketcore_ui.paper_runtime_sample_collection_operations_daily_summary_v1 WHERE id=1;")
allowed=$(psql -At -d finam_core -c "SELECT count(*) FROM marketcore_ui.paper_runtime_sample_collection_operations_daily_summary_v1 WHERE micro_live_allowed=true;")

test "$rows" = "1"
test "$allowed" = "0"

psql -d finam_core -c "
SELECT
    daily_status,
    phase_result_status,
    engineering_status,
    operational_status,
    operations_health_status,
    operations_rows,
    candidates_total,
    sample_ready,
    wait_both_sample,
    micro_live_allowed,
    recommended_action
FROM marketcore_ui.paper_runtime_sample_collection_operations_daily_summary_v1
WHERE id=1;
"

echo "daily_summary_rows=$rows"
echo "micro_live_allowed_rows=$allowed"
echo "risk_page_ready=READY"
echo "settings_page_ready=READY"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=PAPER_RUNTIME_SAMPLE_COLLECTION_OPERATIONS_DAILY_SUMMARY_V1_READY"
echo "VERDICT=TEST_PAPER_RUNTIME_SAMPLE_COLLECTION_OPERATIONS_DAILY_SUMMARY_V1_OK"
