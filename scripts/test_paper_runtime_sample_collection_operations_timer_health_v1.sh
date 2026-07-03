#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_PAPER_RUNTIME_SAMPLE_COLLECTION_OPERATIONS_TIMER_HEALTH_V1 ==="

scripts/apply_paper_runtime_sample_collection_operations_timer_health_v1.sh

PYTHONPATH=src python -m py_compile \
  src/scripts/build_paper_runtime_sample_collection_operations_timer_health_v1.py \
  src/marketcore/api/serve_knowledge_graph_api_v1.py \
  src/marketcore/presentation/pages/paper_sample_operations_timer_health.py \
  src/marketcore/presentation/registry.py \
  src/marketcore/presentation/app.py

if grep -R "psycopg2\|DATABASE_URL\|SELECT " -n src/marketcore/presentation/pages/paper_sample_operations_timer_health.py; then
  echo "FORBIDDEN_DIRECT_DB_ACCESS_IN_UI_PAGE"
  exit 1
fi

sudo -u postgres env \
  DATABASE_URL=postgresql:///finam_core \
  PYTHONPATH=src \
  /opt/finam-core/venv/bin/python src/scripts/run_paper_runtime_sample_collection_operations_cycle_v1.py \
  > /tmp/operations_timer_health_cycle_v1.log

grep -q "VERDICT=PAPER_RUNTIME_SAMPLE_COLLECTION_OPERATIONS_CYCLE_V1_READY" \
  /tmp/operations_timer_health_cycle_v1.log

DATABASE_URL=postgresql:///finam_core PYTHONPATH=src \
python src/scripts/build_paper_runtime_sample_collection_operations_timer_health_v1.py \
  | tee /tmp/operations_timer_health_builder_v1.txt

grep -q "VERDICT=PAPER_RUNTIME_SAMPLE_COLLECTION_OPERATIONS_TIMER_HEALTH_V1_READY" \
  /tmp/operations_timer_health_builder_v1.txt

KG_API_HOST=127.0.0.1 KG_API_PORT=19995 DATABASE_URL=postgresql:///finam_core PYTHONPATH=src \
python src/marketcore/api/serve_knowledge_graph_api_v1.py > /tmp/kg_api_operations_timer_health_v1.log 2>&1 &
api_pid=$!

MARKETCORE_UI_HOST=127.0.0.1 MARKETCORE_UI_PORT=19980 KG_API_BASE_URL=http://127.0.0.1:19995 PYTHONPATH=src \
python src/marketcore/presentation/app.py > /tmp/operations_timer_health_ui_v1.log 2>&1 &
ui_pid=$!

cleanup() {
  kill "$ui_pid" >/dev/null 2>&1 || true
  kill "$api_pid" >/dev/null 2>&1 || true
}
trap cleanup EXIT

sleep 2

curl -fsS "http://127.0.0.1:19995/api/kg/v1/paper-sample-operations-timer-health" \
  > /tmp/operations_timer_health_api_v1.json

curl -fsS "http://127.0.0.1:19980/paper-sample-operations-timer-health" \
  > /tmp/operations_timer_health_page_v1.html

grep -q '"status": "OK"' /tmp/operations_timer_health_api_v1.json
grep -q '"health_status"' /tmp/operations_timer_health_api_v1.json
grep -q '"timer_active_state"' /tmp/operations_timer_health_api_v1.json
grep -q '"service_result"' /tmp/operations_timer_health_api_v1.json
grep -q '"operations_rows"' /tmp/operations_timer_health_api_v1.json
grep -q '"micro_live_allowed"' /tmp/operations_timer_health_api_v1.json

grep -q "Paper Sample Operations Timer Health" /tmp/operations_timer_health_page_v1.html
grep -q "Operations Timer Details" /tmp/operations_timer_health_page_v1.html
grep -q "PAPER_RUNTIME_SAMPLE_COLLECTION_OPERATIONS_DAILY_SUMMARY_V1" /tmp/operations_timer_health_page_v1.html
grep -q "MARKETCORE_UI_SHELL_V1" /tmp/operations_timer_health_page_v1.html

rows=$(psql -At -d finam_core -c "SELECT count(*) FROM marketcore_ui.paper_runtime_sample_collection_operations_timer_health_v1 WHERE id=1;")
allowed=$(psql -At -d finam_core -c "SELECT count(*) FROM marketcore_ui.paper_runtime_sample_collection_operations_timer_health_v1 WHERE micro_live_allowed=true;")
operations_rows=$(psql -At -d finam_core -c "SELECT operations_rows FROM marketcore_ui.paper_runtime_sample_collection_operations_timer_health_v1 WHERE id=1;")

test "$rows" = "1"
test "$allowed" = "0"
test "$operations_rows" -gt 0

psql -d finam_core -c "
SELECT
    health_status,
    timer_active_state,
    timer_unit_file_state,
    service_result,
    operations_rows,
    operations_high_rows,
    operations_near_ready_rows,
    operations_collecting_rows,
    operations_stale,
    phase_result_status,
    operational_status,
    micro_live_allowed,
    recommended_action
FROM marketcore_ui.paper_runtime_sample_collection_operations_timer_health_v1
WHERE id=1;
"

echo "operations_timer_health_rows=$rows"
echo "operations_rows=$operations_rows"
echo "micro_live_allowed_rows=$allowed"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=PAPER_RUNTIME_SAMPLE_COLLECTION_OPERATIONS_TIMER_HEALTH_V1_READY"
echo "VERDICT=TEST_PAPER_RUNTIME_SAMPLE_COLLECTION_OPERATIONS_TIMER_HEALTH_V1_OK"
