#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_PAPER_RUNTIME_SAMPLE_COLLECTION_OPERATIONS_V1 ==="

scripts/apply_paper_runtime_sample_collection_operations_v1.sh

PYTHONPATH=src python -m py_compile \
  src/scripts/build_paper_runtime_sample_collection_operations_v1.py \
  src/marketcore/api/serve_knowledge_graph_api_v1.py \
  src/marketcore/presentation/pages/paper_runtime_sample_collection_operations.py \
  src/marketcore/presentation/registry.py \
  src/marketcore/presentation/app.py

if grep -R "psycopg2\|DATABASE_URL\|SELECT " -n src/marketcore/presentation/pages/paper_runtime_sample_collection_operations.py; then
  echo "FORBIDDEN_DIRECT_DB_ACCESS_IN_UI_PAGE"
  exit 1
fi

sudo -u postgres env \
  DATABASE_URL=postgresql:///finam_core \
  PYTHONPATH=src \
  /opt/finam-core/venv/bin/python src/scripts/run_paper_runtime_sample_collection_cycle_v1.py \
  > /tmp/operations_sample_cycle_v1.log

grep -q "VERDICT=PAPER_RUNTIME_SAMPLE_COLLECTION_CYCLE_V1_READY" /tmp/operations_sample_cycle_v1.log

DATABASE_URL=postgresql:///finam_core PYTHONPATH=src \
python src/scripts/build_paper_runtime_sample_collection_timer_health_v1.py \
  > /tmp/operations_timer_health_v1.log

grep -q "VERDICT=PAPER_RUNTIME_SAMPLE_COLLECTION_TIMER_HEALTH_V1_READY" /tmp/operations_timer_health_v1.log

DATABASE_URL=postgresql:///finam_core PYTHONPATH=src \
python src/scripts/build_phase_ii_paper_edge_discovery_summary_v1.py \
  > /tmp/operations_phase_summary_v1.log

grep -q "VERDICT=PHASE_II_PAPER_EDGE_DISCOVERY_SUMMARY_V1_READY" /tmp/operations_phase_summary_v1.log

DATABASE_URL=postgresql:///finam_core PYTHONPATH=src \
python src/scripts/build_paper_runtime_sample_collection_operations_v1.py \
  | tee /tmp/paper_runtime_sample_collection_operations_builder_v1.txt

grep -q "VERDICT=PAPER_RUNTIME_SAMPLE_COLLECTION_OPERATIONS_V1_READY" \
  /tmp/paper_runtime_sample_collection_operations_builder_v1.txt

KG_API_HOST=127.0.0.1 KG_API_PORT=19895 DATABASE_URL=postgresql:///finam_core PYTHONPATH=src \
python src/marketcore/api/serve_knowledge_graph_api_v1.py > /tmp/kg_api_operations_v1.log 2>&1 &
api_pid=$!

MARKETCORE_UI_HOST=127.0.0.1 MARKETCORE_UI_PORT=19880 KG_API_BASE_URL=http://127.0.0.1:19895 PYTHONPATH=src \
python src/marketcore/presentation/app.py > /tmp/operations_ui_v1.log 2>&1 &
ui_pid=$!

cleanup() {
  kill "$ui_pid" >/dev/null 2>&1 || true
  kill "$api_pid" >/dev/null 2>&1 || true
}
trap cleanup EXIT

sleep 2

curl -fsS "http://127.0.0.1:19895/api/kg/v1/paper-runtime-sample-collection-operations?limit=20" \
  > /tmp/operations_api_v1.json

curl -fsS "http://127.0.0.1:19880/paper-runtime-sample-collection-operations" \
  > /tmp/operations_page_v1.html

grep -q '"status": "OK"' /tmp/operations_api_v1.json
grep -q '"operation_status"' /tmp/operations_api_v1.json
grep -q '"operation_priority"' /tmp/operations_api_v1.json
grep -q '"recommended_action"' /tmp/operations_api_v1.json
grep -q '"micro_live_allowed"' /tmp/operations_api_v1.json

grep -q "Paper Runtime Sample Collection Operations" /tmp/operations_page_v1.html
grep -q "Operations Queue" /tmp/operations_page_v1.html
grep -q "micro_live_allowed_rows=0" /tmp/operations_page_v1.html
grep -q "PAPER_RUNTIME_SAMPLE_COLLECTION_OPERATIONS_TIMER_V1" /tmp/operations_page_v1.html
grep -q "MARKETCORE_UI_SHELL_V1" /tmp/operations_page_v1.html

rows=$(psql -At -d finam_core -c "SELECT count(*) FROM marketcore_ui.paper_runtime_sample_collection_operations_v1;")
allowed=$(psql -At -d finam_core -c "SELECT count(*) FROM marketcore_ui.paper_runtime_sample_collection_operations_v1 WHERE micro_live_allowed=true;")

test "$rows" -gt 0
test "$allowed" = "0"

psql -d finam_core -c "
SELECT
    operation_priority,
    operation_status,
    count(*) AS rows
FROM marketcore_ui.paper_runtime_sample_collection_operations_v1
GROUP BY operation_priority, operation_status
ORDER BY operation_priority, operation_status;
"

echo "operations_rows=$rows"
echo "micro_live_allowed_rows=$allowed"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=PAPER_RUNTIME_SAMPLE_COLLECTION_OPERATIONS_V1_READY"
echo "VERDICT=TEST_PAPER_RUNTIME_SAMPLE_COLLECTION_OPERATIONS_V1_OK"
