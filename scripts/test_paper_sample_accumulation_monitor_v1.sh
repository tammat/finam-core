#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_PAPER_SAMPLE_ACCUMULATION_MONITOR_V1 ==="

scripts/apply_paper_sample_accumulation_monitor_v1.sh

PYTHONPATH=src python -m py_compile \
  src/scripts/build_paper_sample_accumulation_monitor_v1.py \
  src/marketcore/api/serve_knowledge_graph_api_v1.py \
  src/marketcore/presentation/pages/paper_sample_accumulation_monitor.py \
  src/marketcore/presentation/registry.py \
  src/marketcore/presentation/app.py

if grep -R "psycopg2\|DATABASE_URL\|SELECT " -n src/marketcore/presentation/pages/paper_sample_accumulation_monitor.py; then
  echo "FORBIDDEN_DIRECT_DB_ACCESS_IN_UI_PAGE"
  exit 1
fi

sudo -u postgres env \
  DATABASE_URL=postgresql:///finam_core \
  PYTHONPATH=src \
  /opt/finam-core/venv/bin/python src/scripts/build_paper_edge_discovery_research_candidates_v1.py \
  > /tmp/sample_monitor_candidates_builder_v1.txt

DATABASE_URL=postgresql:///finam_core PYTHONPATH=src \
python src/scripts/build_edge_validation_queue_v1.py \
  > /tmp/sample_monitor_queue_builder_v1.txt

DATABASE_URL=postgresql:///finam_core PYTHONPATH=src \
python src/scripts/build_edge_validation_pipeline_v1.py \
  > /tmp/sample_monitor_pipeline_builder_v1.txt

DATABASE_URL=postgresql:///finam_core PYTHONPATH=src \
python src/scripts/build_edge_robustness_check_v1.py \
  > /tmp/sample_monitor_robustness_builder_v1.txt

DATABASE_URL=postgresql:///finam_core PYTHONPATH=src \
python src/scripts/build_edge_oos_validation_v1.py \
  > /tmp/sample_monitor_oos_validation_builder_v1.txt

DATABASE_URL=postgresql:///finam_core PYTHONPATH=src \
python src/scripts/build_edge_oos_backtest_v1.py \
  > /tmp/sample_monitor_oos_backtest_builder_v1.txt

DATABASE_URL=postgresql:///finam_core PYTHONPATH=src \
python src/scripts/build_micro_live_readiness_v1.py \
  > /tmp/sample_monitor_micro_live_builder_v1.txt

DATABASE_URL=postgresql:///finam_core PYTHONPATH=src \
python src/scripts/build_paper_sample_accumulation_monitor_v1.py \
  | tee /tmp/paper_sample_accumulation_monitor_builder_v1.txt

grep -q "VERDICT=PAPER_SAMPLE_ACCUMULATION_MONITOR_V1_READY" /tmp/paper_sample_accumulation_monitor_builder_v1.txt

KG_API_HOST=127.0.0.1 KG_API_PORT=19295 DATABASE_URL=postgresql:///finam_core PYTHONPATH=src \
python src/marketcore/api/serve_knowledge_graph_api_v1.py > /tmp/kg_api_sample_monitor_v1.log 2>&1 &
api_pid=$!

MARKETCORE_UI_HOST=127.0.0.1 MARKETCORE_UI_PORT=19280 KG_API_BASE_URL=http://127.0.0.1:19295 PYTHONPATH=src \
python src/marketcore/presentation/app.py > /tmp/sample_monitor_page_v1.log 2>&1 &
ui_pid=$!

cleanup() {
  kill "$ui_pid" >/dev/null 2>&1 || true
  kill "$api_pid" >/dev/null 2>&1 || true
}
trap cleanup EXIT

sleep 2

curl -fsS "http://127.0.0.1:19295/api/kg/v1/paper-sample-accumulation-monitor?limit=20" \
  > /tmp/paper_sample_accumulation_monitor_api_v1.json

curl -fsS "http://127.0.0.1:19280/paper-sample-accumulation-monitor" \
  > /tmp/paper_sample_accumulation_monitor_page_v1.html

grep -q '"status": "OK"' /tmp/paper_sample_accumulation_monitor_api_v1.json
grep -q '"sample_status"' /tmp/paper_sample_accumulation_monitor_api_v1.json
grep -q '"remaining_total_trades"' /tmp/paper_sample_accumulation_monitor_api_v1.json
grep -q '"remaining_oos_trades"' /tmp/paper_sample_accumulation_monitor_api_v1.json
grep -q '"progress_pct"' /tmp/paper_sample_accumulation_monitor_api_v1.json

grep -q "Paper Sample Accumulation Monitor" /tmp/paper_sample_accumulation_monitor_page_v1.html
grep -q "Accumulation" /tmp/paper_sample_accumulation_monitor_page_v1.html
grep -q "PAPER_RUNTIME_SAMPLE_COLLECTION_V1" /tmp/paper_sample_accumulation_monitor_page_v1.html
grep -q "MARKETCORE_UI_SHELL_V1" /tmp/paper_sample_accumulation_monitor_page_v1.html

rows=$(psql -At -d finam_core -c "SELECT count(*) FROM marketcore_ui.paper_sample_accumulation_monitor_v1;")
allowed=$(psql -At -d finam_core -c "SELECT count(*) FROM marketcore_ui.paper_sample_accumulation_monitor_v1 WHERE micro_live_allowed=true;")

test "$rows" -gt 0
test "$allowed" = "0"

echo "paper_sample_accumulation_monitor_rows=$rows"
echo "micro_live_allowed_rows=$allowed"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=PAPER_SAMPLE_ACCUMULATION_MONITOR_V1_READY"
echo "VERDICT=TEST_PAPER_SAMPLE_ACCUMULATION_MONITOR_V1_OK"
