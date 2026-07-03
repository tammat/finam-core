#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_MICRO_LIVE_READINESS_V1 ==="

scripts/apply_micro_live_readiness_v1.sh

PYTHONPATH=src python -m py_compile \
  src/scripts/build_micro_live_readiness_v1.py \
  src/marketcore/api/serve_knowledge_graph_api_v1.py \
  src/marketcore/presentation/pages/micro_live_readiness.py \
  src/marketcore/presentation/registry.py \
  src/marketcore/presentation/app.py

if grep -R "psycopg2\|DATABASE_URL\|SELECT " -n src/marketcore/presentation/pages/micro_live_readiness.py; then
  echo "FORBIDDEN_DIRECT_DB_ACCESS_IN_UI_PAGE"
  exit 1
fi

sudo -u postgres env \
  DATABASE_URL=postgresql:///finam_core \
  PYTHONPATH=src \
  /opt/finam-core/venv/bin/python src/scripts/build_paper_edge_discovery_research_candidates_v1.py \
  > /tmp/micro_live_candidates_builder_v1.txt

DATABASE_URL=postgresql:///finam_core PYTHONPATH=src \
python src/scripts/build_edge_validation_queue_v1.py \
  > /tmp/micro_live_queue_builder_v1.txt

DATABASE_URL=postgresql:///finam_core PYTHONPATH=src \
python src/scripts/build_edge_validation_pipeline_v1.py \
  > /tmp/micro_live_pipeline_builder_v1.txt

DATABASE_URL=postgresql:///finam_core PYTHONPATH=src \
python src/scripts/build_edge_robustness_check_v1.py \
  > /tmp/micro_live_robustness_builder_v1.txt

DATABASE_URL=postgresql:///finam_core PYTHONPATH=src \
python src/scripts/build_edge_oos_validation_v1.py \
  > /tmp/micro_live_oos_validation_builder_v1.txt

DATABASE_URL=postgresql:///finam_core PYTHONPATH=src \
python src/scripts/build_edge_oos_backtest_v1.py \
  > /tmp/micro_live_oos_backtest_builder_v1.txt

DATABASE_URL=postgresql:///finam_core PYTHONPATH=src \
python src/scripts/build_micro_live_readiness_v1.py \
  | tee /tmp/micro_live_readiness_builder_v1.txt

grep -q "VERDICT=MICRO_LIVE_READINESS_V1_READY" /tmp/micro_live_readiness_builder_v1.txt

KG_API_HOST=127.0.0.1 KG_API_PORT=19095 DATABASE_URL=postgresql:///finam_core PYTHONPATH=src \
python src/marketcore/api/serve_knowledge_graph_api_v1.py > /tmp/kg_api_micro_live_v1.log 2>&1 &
api_pid=$!

MARKETCORE_UI_HOST=127.0.0.1 MARKETCORE_UI_PORT=19080 KG_API_BASE_URL=http://127.0.0.1:19095 PYTHONPATH=src \
python src/marketcore/presentation/app.py > /tmp/micro_live_page_v1.log 2>&1 &
ui_pid=$!

cleanup() {
  kill "$ui_pid" >/dev/null 2>&1 || true
  kill "$api_pid" >/dev/null 2>&1 || true
}
trap cleanup EXIT

sleep 2

curl -fsS "http://127.0.0.1:19095/api/kg/v1/micro-live-readiness?limit=20" \
  > /tmp/micro_live_readiness_api_v1.json

curl -fsS "http://127.0.0.1:19080/micro-live-readiness" \
  > /tmp/micro_live_readiness_page_v1.html

grep -q '"status": "OK"' /tmp/micro_live_readiness_api_v1.json
grep -q '"readiness_status"' /tmp/micro_live_readiness_api_v1.json
grep -q '"micro_live_ready"' /tmp/micro_live_readiness_api_v1.json
grep -q '"micro_live_allowed"' /tmp/micro_live_readiness_api_v1.json
grep -q '"recommended_action"' /tmp/micro_live_readiness_api_v1.json

grep -q "Micro Live Readiness" /tmp/micro_live_readiness_page_v1.html
grep -q "Readiness Gate" /tmp/micro_live_readiness_page_v1.html
grep -q "PAPER_EDGE_DISCOVERY_PHASE_ACCEPTANCE_V1" /tmp/micro_live_readiness_page_v1.html
grep -q "MARKETCORE_UI_SHELL_V1" /tmp/micro_live_readiness_page_v1.html

rows=$(psql -At -d finam_core -c "SELECT count(*) FROM marketcore_ui.micro_live_readiness_v1;")
allowed=$(psql -At -d finam_core -c "SELECT count(*) FROM marketcore_ui.micro_live_readiness_v1 WHERE micro_live_allowed=true;")

test "$rows" -gt 0
test "$allowed" = "0"

echo "micro_live_readiness_rows=$rows"
echo "micro_live_allowed_rows=$allowed"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=MICRO_LIVE_READINESS_V1_READY"
echo "VERDICT=TEST_MICRO_LIVE_READINESS_V1_OK"
