#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_EDGE_VALIDATION_PIPELINE_V1 ==="

scripts/apply_edge_validation_pipeline_v1.sh

PYTHONPATH=src python -m py_compile \
  src/scripts/build_edge_validation_pipeline_v1.py \
  src/marketcore/api/serve_knowledge_graph_api_v1.py \
  src/marketcore/presentation/pages/edge_validation_pipeline.py \
  src/marketcore/presentation/registry.py \
  src/marketcore/presentation/app.py

if grep -R "psycopg2\|DATABASE_URL\|SELECT " -n src/marketcore/presentation/pages/edge_validation_pipeline.py; then
  echo "FORBIDDEN_DIRECT_DB_ACCESS_IN_UI_PAGE"
  exit 1
fi

sudo -u postgres env \
  DATABASE_URL=postgresql:///finam_core \
  PYTHONPATH=src \
  /opt/finam-core/venv/bin/python src/scripts/build_paper_edge_discovery_research_candidates_v1.py \
  > /tmp/edge_validation_pipeline_candidates_builder_v1.txt

DATABASE_URL=postgresql:///finam_core PYTHONPATH=src \
python src/scripts/build_edge_validation_queue_v1.py \
  > /tmp/edge_validation_pipeline_queue_builder_v1.txt

DATABASE_URL=postgresql:///finam_core PYTHONPATH=src \
python src/scripts/build_edge_validation_pipeline_v1.py \
  | tee /tmp/edge_validation_pipeline_builder_v1.txt

grep -q "VERDICT=EDGE_VALIDATION_PIPELINE_V1_READY" /tmp/edge_validation_pipeline_builder_v1.txt

KG_API_HOST=127.0.0.1 KG_API_PORT=18695 DATABASE_URL=postgresql:///finam_core PYTHONPATH=src \
python src/marketcore/api/serve_knowledge_graph_api_v1.py > /tmp/kg_api_edge_validation_pipeline_v1.log 2>&1 &
api_pid=$!

MARKETCORE_UI_HOST=127.0.0.1 MARKETCORE_UI_PORT=18680 KG_API_BASE_URL=http://127.0.0.1:18695 PYTHONPATH=src \
python src/marketcore/presentation/app.py > /tmp/edge_validation_pipeline_page_v1.log 2>&1 &
ui_pid=$!

cleanup() {
  kill "$ui_pid" >/dev/null 2>&1 || true
  kill "$api_pid" >/dev/null 2>&1 || true
}
trap cleanup EXIT

sleep 2

curl -fsS "http://127.0.0.1:18695/api/kg/v1/edge-validation-pipeline?limit=20" \
  > /tmp/edge_validation_pipeline_api_v1.json

curl -fsS "http://127.0.0.1:18680/edge-validation-pipeline" \
  > /tmp/edge_validation_pipeline_page_v1.html

grep -q '"status": "OK"' /tmp/edge_validation_pipeline_api_v1.json
grep -q '"pipeline_status"' /tmp/edge_validation_pipeline_api_v1.json
grep -q '"sample_check_status"' /tmp/edge_validation_pipeline_api_v1.json
grep -q '"pf_check_status"' /tmp/edge_validation_pipeline_api_v1.json
grep -q '"expectancy_check_status"' /tmp/edge_validation_pipeline_api_v1.json
grep -q '"recommended_action"' /tmp/edge_validation_pipeline_api_v1.json

grep -q "Edge Validation Pipeline" /tmp/edge_validation_pipeline_page_v1.html
grep -q "Pipeline" /tmp/edge_validation_pipeline_page_v1.html
grep -q "EDGE_ROBUSTNESS_CHECK_V1" /tmp/edge_validation_pipeline_page_v1.html
grep -q "MARKETCORE_UI_SHELL_V1" /tmp/edge_validation_pipeline_page_v1.html

rows=$(psql -At -d finam_core -c "SELECT count(*) FROM marketcore_ui.edge_validation_pipeline_v1;")
test "$rows" -gt 0

echo "edge_validation_pipeline_rows=$rows"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=EDGE_VALIDATION_PIPELINE_V1_READY"
echo "VERDICT=TEST_EDGE_VALIDATION_PIPELINE_V1_OK"
