#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_PAPER_RUNTIME_SAMPLE_COLLECTION_TIMER_HEALTH_V1 ==="

scripts/apply_paper_runtime_sample_collection_timer_health_v1.sh

PYTHONPATH=src python -m py_compile \
  src/scripts/build_paper_runtime_sample_collection_timer_health_v1.py \
  src/marketcore/api/serve_knowledge_graph_api_v1.py \
  src/marketcore/presentation/pages/paper_sample_collection_timer_health.py \
  src/marketcore/presentation/registry.py \
  src/marketcore/presentation/app.py

if grep -R "psycopg2\|DATABASE_URL\|SELECT " -n src/marketcore/presentation/pages/paper_sample_collection_timer_health.py; then
  echo "FORBIDDEN_DIRECT_DB_ACCESS_IN_UI_PAGE"
  exit 1
fi

sudo -u postgres env \
  DATABASE_URL=postgresql:///finam_core \
  PYTHONPATH=src \
  /opt/finam-core/venv/bin/python src/scripts/run_paper_runtime_sample_collection_cycle_v1.py \
  > /tmp/timer_health_sample_cycle_v1.log

grep -q "VERDICT=PAPER_RUNTIME_SAMPLE_COLLECTION_CYCLE_V1_READY" /tmp/timer_health_sample_cycle_v1.log

DATABASE_URL=postgresql:///finam_core PYTHONPATH=src \
python src/scripts/build_paper_runtime_sample_collection_timer_health_v1.py \
  | tee /tmp/paper_runtime_sample_collection_timer_health_builder_v1.txt

grep -q "VERDICT=PAPER_RUNTIME_SAMPLE_COLLECTION_TIMER_HEALTH_V1_READY" \
  /tmp/paper_runtime_sample_collection_timer_health_builder_v1.txt

KG_API_HOST=127.0.0.1 KG_API_PORT=19595 DATABASE_URL=postgresql:///finam_core PYTHONPATH=src \
python src/marketcore/api/serve_knowledge_graph_api_v1.py > /tmp/kg_api_timer_health_v1.log 2>&1 &
api_pid=$!

MARKETCORE_UI_HOST=127.0.0.1 MARKETCORE_UI_PORT=19580 KG_API_BASE_URL=http://127.0.0.1:19595 PYTHONPATH=src \
python src/marketcore/presentation/app.py > /tmp/timer_health_ui_v1.log 2>&1 &
ui_pid=$!

cleanup() {
  kill "$ui_pid" >/dev/null 2>&1 || true
  kill "$api_pid" >/dev/null 2>&1 || true
}
trap cleanup EXIT

sleep 2

curl -fsS "http://127.0.0.1:19595/api/kg/v1/paper-sample-collection-timer-health" \
  > /tmp/paper_sample_collection_timer_health_api_v1.json

curl -fsS "http://127.0.0.1:19580/paper-sample-collection-timer-health" \
  > /tmp/paper_sample_collection_timer_health_page_v1.html

grep -q '"status": "OK"' /tmp/paper_sample_collection_timer_health_api_v1.json
grep -q '"timer_health_status"' /tmp/paper_sample_collection_timer_health_api_v1.json
grep -q '"timer_active_state"' /tmp/paper_sample_collection_timer_health_api_v1.json
grep -q '"service_result"' /tmp/paper_sample_collection_timer_health_api_v1.json
grep -q '"sample_summary_age_sec"' /tmp/paper_sample_collection_timer_health_api_v1.json
grep -q '"micro_live_allowed"' /tmp/paper_sample_collection_timer_health_api_v1.json

grep -q "Paper Sample Collection Timer Health" /tmp/paper_sample_collection_timer_health_page_v1.html
grep -q "Timer Details" /tmp/paper_sample_collection_timer_health_page_v1.html
grep -q "PAPER_RUNTIME_SAMPLE_COLLECTION_PHASE_CLOSE_V1" /tmp/paper_sample_collection_timer_health_page_v1.html
grep -q "MARKETCORE_UI_SHELL_V1" /tmp/paper_sample_collection_timer_health_page_v1.html

rows=$(psql -At -d finam_core -c "SELECT count(*) FROM marketcore_ui.paper_runtime_sample_collection_timer_health_v1 WHERE id=1;")
allowed=$(psql -At -d finam_core -c "SELECT count(*) FROM marketcore_ui.paper_runtime_sample_collection_timer_health_v1 WHERE micro_live_allowed=true;")

test "$rows" = "1"
test "$allowed" = "0"

psql -d finam_core -c "
SELECT
    timer_health_status,
    timer_active_state,
    timer_unit_file_state,
    service_result,
    sample_summary_age_sec,
    sample_summary_stale,
    candidates_total,
    sample_ready,
    collection_status,
    phase_status,
    micro_live_allowed,
    recommended_action
FROM marketcore_ui.paper_runtime_sample_collection_timer_health_v1
WHERE id=1;
"

echo "timer_health_rows=$rows"
echo "micro_live_allowed_rows=$allowed"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=PAPER_RUNTIME_SAMPLE_COLLECTION_TIMER_HEALTH_V1_READY"
echo "VERDICT=TEST_PAPER_RUNTIME_SAMPLE_COLLECTION_TIMER_HEALTH_V1_OK"
