#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_PHASE_II_PAPER_EDGE_DISCOVERY_SUMMARY_V1 ==="

scripts/apply_phase_ii_paper_edge_discovery_summary_v1.sh

PYTHONPATH=src python -m py_compile \
  src/scripts/build_phase_ii_paper_edge_discovery_summary_v1.py \
  src/marketcore/api/serve_knowledge_graph_api_v1.py \
  src/marketcore/presentation/pages/phase_ii_paper_edge_discovery_summary.py \
  src/marketcore/presentation/registry.py \
  src/marketcore/presentation/app.py

if grep -R "psycopg2\|DATABASE_URL\|SELECT " -n src/marketcore/presentation/pages/phase_ii_paper_edge_discovery_summary.py; then
  echo "FORBIDDEN_DIRECT_DB_ACCESS_IN_UI_PAGE"
  exit 1
fi

sudo -u postgres env \
  DATABASE_URL=postgresql:///finam_core \
  PYTHONPATH=src \
  /opt/finam-core/venv/bin/python src/scripts/run_paper_runtime_sample_collection_cycle_v1.py \
  > /tmp/phase_ii_summary_sample_cycle_v1.log

grep -q "VERDICT=PAPER_RUNTIME_SAMPLE_COLLECTION_CYCLE_V1_READY" /tmp/phase_ii_summary_sample_cycle_v1.log

DATABASE_URL=postgresql:///finam_core PYTHONPATH=src \
python src/scripts/build_paper_runtime_sample_collection_timer_health_v1.py \
  > /tmp/phase_ii_summary_timer_health_v1.log

grep -q "VERDICT=PAPER_RUNTIME_SAMPLE_COLLECTION_TIMER_HEALTH_V1_READY" /tmp/phase_ii_summary_timer_health_v1.log

DATABASE_URL=postgresql:///finam_core PYTHONPATH=src \
python src/scripts/build_paper_runtime_sample_collection_phase_close_v1.py \
  > /tmp/phase_ii_summary_phase_close_v1.log

grep -q "VERDICT=PAPER_RUNTIME_SAMPLE_COLLECTION_PHASE_CLOSE_V1_READY" /tmp/phase_ii_summary_phase_close_v1.log

DATABASE_URL=postgresql:///finam_core PYTHONPATH=src \
python src/scripts/build_phase_ii_paper_edge_discovery_summary_v1.py \
  | tee /tmp/phase_ii_paper_edge_discovery_summary_builder_v1.txt

grep -q "VERDICT=PHASE_II_PAPER_EDGE_DISCOVERY_SUMMARY_V1_READY" \
  /tmp/phase_ii_paper_edge_discovery_summary_builder_v1.txt

KG_API_HOST=127.0.0.1 KG_API_PORT=19795 DATABASE_URL=postgresql:///finam_core PYTHONPATH=src \
python src/marketcore/api/serve_knowledge_graph_api_v1.py > /tmp/kg_api_phase_ii_summary_v1.log 2>&1 &
api_pid=$!

MARKETCORE_UI_HOST=127.0.0.1 MARKETCORE_UI_PORT=19780 KG_API_BASE_URL=http://127.0.0.1:19795 PYTHONPATH=src \
python src/marketcore/presentation/app.py > /tmp/phase_ii_summary_ui_v1.log 2>&1 &
ui_pid=$!

cleanup() {
  kill "$ui_pid" >/dev/null 2>&1 || true
  kill "$api_pid" >/dev/null 2>&1 || true
}
trap cleanup EXIT

sleep 2

curl -fsS "http://127.0.0.1:19795/api/kg/v1/phase-ii-paper-edge-discovery-summary" \
  > /tmp/phase_ii_summary_api_v1.json

curl -fsS "http://127.0.0.1:19780/phase-ii-paper-edge-discovery-summary" \
  > /tmp/phase_ii_summary_page_v1.html

grep -q '"status": "OK"' /tmp/phase_ii_summary_api_v1.json
grep -q '"phase_result_status"' /tmp/phase_ii_summary_api_v1.json
grep -q '"engineering_status"' /tmp/phase_ii_summary_api_v1.json
grep -q '"operational_status"' /tmp/phase_ii_summary_api_v1.json
grep -q '"micro_live_allowed"' /tmp/phase_ii_summary_api_v1.json
grep -q '"next_phase"' /tmp/phase_ii_summary_api_v1.json

grep -q "Phase II Paper Edge Discovery Summary" /tmp/phase_ii_summary_page_v1.html
grep -q "Pipeline Row Coverage" /tmp/phase_ii_summary_page_v1.html
grep -q "PHASE_II_PAPER_EDGE_DISCOVERY_SUMMARY_V1" /tmp/phase_ii_summary_page_v1.html
grep -q "MARKETCORE_UI_SHELL_V1" /tmp/phase_ii_summary_page_v1.html

rows=$(psql -At -d finam_core -c "SELECT count(*) FROM marketcore_ui.phase_ii_paper_edge_discovery_summary_v1 WHERE id=1;")
allowed=$(psql -At -d finam_core -c "SELECT count(*) FROM marketcore_ui.phase_ii_paper_edge_discovery_summary_v1 WHERE micro_live_allowed=true;")
engineering_status=$(psql -At -d finam_core -c "SELECT engineering_status FROM marketcore_ui.phase_ii_paper_edge_discovery_summary_v1 WHERE id=1;")

test "$rows" = "1"
test "$allowed" = "0"
test "$engineering_status" = "CLOSED"

psql -d finam_core -c "
SELECT
    phase_result_status,
    engineering_status,
    operational_status,
    close_status,
    timer_health_status,
    candidates_total,
    sample_ready,
    wait_both_sample,
    micro_live_allowed_rows,
    micro_live_allowed,
    next_phase,
    recommended_action
FROM marketcore_ui.phase_ii_paper_edge_discovery_summary_v1
WHERE id=1;
"

echo "phase_ii_summary_rows=$rows"
echo "engineering_status=$engineering_status"
echo "micro_live_allowed_rows=$allowed"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=PHASE_II_PAPER_EDGE_DISCOVERY_SUMMARY_V1_READY"
echo "VERDICT=TEST_PHASE_II_PAPER_EDGE_DISCOVERY_SUMMARY_V1_OK"
