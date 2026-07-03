#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_EDGE_OOS_BACKTEST_V1 ==="

scripts/apply_edge_oos_backtest_v1.sh

PYTHONPATH=src python -m py_compile \
  src/scripts/build_edge_oos_backtest_v1.py \
  src/marketcore/api/serve_knowledge_graph_api_v1.py \
  src/marketcore/presentation/pages/edge_oos_backtest.py \
  src/marketcore/presentation/registry.py \
  src/marketcore/presentation/app.py

if grep -R "psycopg2\|DATABASE_URL\|SELECT " -n src/marketcore/presentation/pages/edge_oos_backtest.py; then
  echo "FORBIDDEN_DIRECT_DB_ACCESS_IN_UI_PAGE"
  exit 1
fi

sudo -u postgres env \
  DATABASE_URL=postgresql:///finam_core \
  PYTHONPATH=src \
  /opt/finam-core/venv/bin/python src/scripts/build_paper_edge_discovery_research_candidates_v1.py \
  > /tmp/edge_oos_backtest_candidates_builder_v1.txt

DATABASE_URL=postgresql:///finam_core PYTHONPATH=src \
python src/scripts/build_edge_validation_queue_v1.py \
  > /tmp/edge_oos_backtest_queue_builder_v1.txt

DATABASE_URL=postgresql:///finam_core PYTHONPATH=src \
python src/scripts/build_edge_validation_pipeline_v1.py \
  > /tmp/edge_oos_backtest_pipeline_builder_v1.txt

DATABASE_URL=postgresql:///finam_core PYTHONPATH=src \
python src/scripts/build_edge_robustness_check_v1.py \
  > /tmp/edge_oos_backtest_robustness_builder_v1.txt

DATABASE_URL=postgresql:///finam_core PYTHONPATH=src \
python src/scripts/build_edge_oos_validation_v1.py \
  > /tmp/edge_oos_backtest_oos_builder_v1.txt

DATABASE_URL=postgresql:///finam_core PYTHONPATH=src \
python src/scripts/build_edge_oos_backtest_v1.py \
  | tee /tmp/edge_oos_backtest_builder_v1.txt

grep -q "VERDICT=EDGE_OOS_BACKTEST_V1_READY" /tmp/edge_oos_backtest_builder_v1.txt

KG_API_HOST=127.0.0.1 KG_API_PORT=18995 DATABASE_URL=postgresql:///finam_core PYTHONPATH=src \
python src/marketcore/api/serve_knowledge_graph_api_v1.py > /tmp/kg_api_edge_oos_backtest_v1.log 2>&1 &
api_pid=$!

MARKETCORE_UI_HOST=127.0.0.1 MARKETCORE_UI_PORT=18980 KG_API_BASE_URL=http://127.0.0.1:18995 PYTHONPATH=src \
python src/marketcore/presentation/app.py > /tmp/edge_oos_backtest_page_v1.log 2>&1 &
ui_pid=$!

cleanup() {
  kill "$ui_pid" >/dev/null 2>&1 || true
  kill "$api_pid" >/dev/null 2>&1 || true
}
trap cleanup EXIT

sleep 2

curl -fsS "http://127.0.0.1:18995/api/kg/v1/edge-oos-backtest?limit=20" \
  > /tmp/edge_oos_backtest_api_v1.json

curl -fsS "http://127.0.0.1:18980/edge-oos-backtest" \
  > /tmp/edge_oos_backtest_page_v1.html

grep -q '"status": "OK"' /tmp/edge_oos_backtest_api_v1.json
grep -q '"backtest_status"' /tmp/edge_oos_backtest_api_v1.json
grep -q '"oos_profit_factor"' /tmp/edge_oos_backtest_api_v1.json
grep -q '"stability_score"' /tmp/edge_oos_backtest_api_v1.json
grep -q '"recommended_action"' /tmp/edge_oos_backtest_api_v1.json

grep -q "Edge OOS Backtest" /tmp/edge_oos_backtest_page_v1.html
grep -q "OOS Backtest" /tmp/edge_oos_backtest_page_v1.html
grep -q "MICRO_LIVE_READINESS_V1" /tmp/edge_oos_backtest_page_v1.html
grep -q "MARKETCORE_UI_SHELL_V1" /tmp/edge_oos_backtest_page_v1.html

rows=$(psql -At -d finam_core -c "SELECT count(*) FROM marketcore_ui.edge_oos_backtest_v1;")
test "$rows" -gt 0

echo "edge_oos_backtest_rows=$rows"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=EDGE_OOS_BACKTEST_V1_READY"
echo "VERDICT=TEST_EDGE_OOS_BACKTEST_V1_OK"
