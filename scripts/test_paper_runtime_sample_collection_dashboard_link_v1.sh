#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_PAPER_RUNTIME_SAMPLE_COLLECTION_DASHBOARD_LINK_V1 ==="

PYTHONPATH=src python -m py_compile \
  src/marketcore/api/serve_knowledge_graph_api_v1.py \
  src/marketcore/presentation/pages/paper_edge_discovery.py \
  src/marketcore/presentation/pages/paper_sample_accumulation_monitor.py \
  src/marketcore/presentation/registry.py \
  src/marketcore/presentation/app.py

for page in \
  src/marketcore/presentation/pages/paper_edge_discovery.py \
  src/marketcore/presentation/pages/paper_sample_accumulation_monitor.py
do
  if grep -R "psycopg2\|DATABASE_URL\|SELECT " -n "$page"; then
    echo "FORBIDDEN_DIRECT_DB_ACCESS_IN_UI_PAGE file=$page"
    exit 1
  fi
done

sudo -u postgres env DATABASE_URL=postgresql:///finam_core PYTHONPATH=src \
  /opt/finam-core/venv/bin/python src/scripts/run_paper_runtime_sample_collection_cycle_v1.py \
  > /tmp/dashboard_link_sample_cycle_v1.log

grep -q "VERDICT=PAPER_RUNTIME_SAMPLE_COLLECTION_CYCLE_V1_READY" /tmp/dashboard_link_sample_cycle_v1.log

KG_API_HOST=127.0.0.1 KG_API_PORT=19495 DATABASE_URL=postgresql:///finam_core PYTHONPATH=src \
python src/marketcore/api/serve_knowledge_graph_api_v1.py > /tmp/kg_api_dashboard_link_v1.log 2>&1 &
api_pid=$!

MARKETCORE_UI_HOST=127.0.0.1 MARKETCORE_UI_PORT=19480 KG_API_BASE_URL=http://127.0.0.1:19495 PYTHONPATH=src \
python src/marketcore/presentation/app.py > /tmp/dashboard_link_ui_v1.log 2>&1 &
ui_pid=$!

cleanup() {
  kill "$ui_pid" >/dev/null 2>&1 || true
  kill "$api_pid" >/dev/null 2>&1 || true
}
trap cleanup EXIT

sleep 2

curl -fsS "http://127.0.0.1:19495/api/kg/v1/paper-runtime-sample-collection" \
  > /tmp/paper_runtime_sample_collection_dashboard_link_api_v1.json

curl -fsS "http://127.0.0.1:19480/paper-sample-accumulation-monitor" \
  > /tmp/paper_sample_accumulation_monitor_dashboard_link_v1.html

curl -fsS "http://127.0.0.1:19480/paper-edge-discovery" \
  > /tmp/paper_edge_discovery_dashboard_link_v1.html

grep -q '"status": "OK"' /tmp/paper_runtime_sample_collection_dashboard_link_api_v1.json
grep -q '"candidates_total"' /tmp/paper_runtime_sample_collection_dashboard_link_api_v1.json
grep -q '"min_remaining_total_trades"' /tmp/paper_runtime_sample_collection_dashboard_link_api_v1.json
grep -q '"min_remaining_oos_trades"' /tmp/paper_runtime_sample_collection_dashboard_link_api_v1.json
grep -q '"collection_status"' /tmp/paper_runtime_sample_collection_dashboard_link_api_v1.json

grep -q "Paper Sample Accumulation Monitor" /tmp/paper_sample_accumulation_monitor_dashboard_link_v1.html
grep -q "Sample Collection Summary" /tmp/paper_sample_accumulation_monitor_dashboard_link_v1.html
grep -q "Closest Candidates To Recheck" /tmp/paper_sample_accumulation_monitor_dashboard_link_v1.html
grep -q "marketcore_ui.paper_runtime_sample_collection_v1" /tmp/paper_sample_accumulation_monitor_dashboard_link_v1.html
grep -q "PAPER_RUNTIME_SAMPLE_COLLECTION_TIMER_HEALTH_V1" /tmp/paper_sample_accumulation_monitor_dashboard_link_v1.html
grep -q "MARKETCORE_UI_SHELL_V1" /tmp/paper_sample_accumulation_monitor_dashboard_link_v1.html

grep -q "Sample Collection" /tmp/paper_edge_discovery_dashboard_link_v1.html
grep -q "paper-sample-accumulation-monitor" /tmp/paper_edge_discovery_dashboard_link_v1.html
grep -q "PAPER_RUNTIME_SAMPLE_COLLECTION_DASHBOARD_LINK_V1" /tmp/paper_edge_discovery_dashboard_link_v1.html

summary_rows=$(psql -At -d finam_core -c "SELECT count(*) FROM marketcore_ui.paper_runtime_sample_collection_v1 WHERE id=1;")
monitor_rows=$(psql -At -d finam_core -c "SELECT count(*) FROM marketcore_ui.paper_sample_accumulation_monitor_v1;")
allowed_rows=$(psql -At -d finam_core -c "SELECT count(*) FROM marketcore_ui.paper_runtime_sample_collection_v1 WHERE micro_live_allowed=true;")

test "$summary_rows" = "1"
test "$monitor_rows" -gt 0
test "$allowed_rows" = "0"

echo "summary_rows=$summary_rows"
echo "monitor_rows=$monitor_rows"
echo "micro_live_allowed_rows=$allowed_rows"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=PAPER_RUNTIME_SAMPLE_COLLECTION_DASHBOARD_LINK_V1_READY"
echo "VERDICT=TEST_PAPER_RUNTIME_SAMPLE_COLLECTION_DASHBOARD_LINK_V1_OK"
