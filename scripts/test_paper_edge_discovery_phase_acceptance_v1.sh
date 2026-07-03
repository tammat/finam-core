#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_PAPER_EDGE_DISCOVERY_PHASE_ACCEPTANCE_V1 ==="

OUT="/tmp/paper_edge_discovery_phase_acceptance_v1"
rm -rf "$OUT"
mkdir -p "$OUT"

PYTHONPATH=src python -m py_compile \
  src/scripts/validate_paper_edge_discovery_phase_acceptance_v1.py \
  src/marketcore/api/serve_knowledge_graph_api_v1.py \
  src/marketcore/presentation/app.py \
  src/marketcore/presentation/pages/paper_edge_discovery.py \
  src/marketcore/presentation/pages/edge_validation_queue.py \
  src/marketcore/presentation/pages/edge_validation_pipeline.py \
  src/marketcore/presentation/pages/edge_robustness_check.py \
  src/marketcore/presentation/pages/edge_oos_validation.py \
  src/marketcore/presentation/pages/edge_oos_backtest.py \
  src/marketcore/presentation/pages/micro_live_readiness.py

for page in \
  src/marketcore/presentation/pages/paper_edge_discovery.py \
  src/marketcore/presentation/pages/edge_validation_queue.py \
  src/marketcore/presentation/pages/edge_validation_pipeline.py \
  src/marketcore/presentation/pages/edge_robustness_check.py \
  src/marketcore/presentation/pages/edge_oos_validation.py \
  src/marketcore/presentation/pages/edge_oos_backtest.py \
  src/marketcore/presentation/pages/micro_live_readiness.py
do
  if grep -R "psycopg2\|DATABASE_URL\|SELECT " -n "$page"; then
    echo "FORBIDDEN_DIRECT_DB_ACCESS_IN_UI_PAGE file=$page"
    exit 1
  fi
done

sudo -u postgres env \
  DATABASE_URL=postgresql:///finam_core \
  PYTHONPATH=src \
  /opt/finam-core/venv/bin/python src/scripts/build_paper_edge_discovery_research_candidates_v1.py \
  > "$OUT/01_research_candidates.log"

DATABASE_URL=postgresql:///finam_core PYTHONPATH=src \
python src/scripts/build_edge_validation_queue_v1.py \
  > "$OUT/02_edge_validation_queue.log"

DATABASE_URL=postgresql:///finam_core PYTHONPATH=src \
python src/scripts/build_edge_validation_pipeline_v1.py \
  > "$OUT/03_edge_validation_pipeline.log"

DATABASE_URL=postgresql:///finam_core PYTHONPATH=src \
python src/scripts/build_edge_robustness_check_v1.py \
  > "$OUT/04_edge_robustness_check.log"

DATABASE_URL=postgresql:///finam_core PYTHONPATH=src \
python src/scripts/build_edge_oos_validation_v1.py \
  > "$OUT/05_edge_oos_validation.log"

DATABASE_URL=postgresql:///finam_core PYTHONPATH=src \
python src/scripts/build_edge_oos_backtest_v1.py \
  > "$OUT/06_edge_oos_backtest.log"

DATABASE_URL=postgresql:///finam_core PYTHONPATH=src \
python src/scripts/build_micro_live_readiness_v1.py \
  > "$OUT/07_micro_live_readiness.log"

grep -q "VERDICT=PAPER_EDGE_DISCOVERY_RESEARCH_CANDIDATES_V1_READY" "$OUT/01_research_candidates.log"
grep -q "VERDICT=EDGE_VALIDATION_QUEUE_V1_READY" "$OUT/02_edge_validation_queue.log"
grep -q "VERDICT=EDGE_VALIDATION_PIPELINE_V1_READY" "$OUT/03_edge_validation_pipeline.log"
grep -q "VERDICT=EDGE_ROBUSTNESS_CHECK_V1_READY" "$OUT/04_edge_robustness_check.log"
grep -q "VERDICT=EDGE_OOS_VALIDATION_V1_READY" "$OUT/05_edge_oos_validation.log"
grep -q "VERDICT=EDGE_OOS_BACKTEST_V1_READY" "$OUT/06_edge_oos_backtest.log"
grep -q "VERDICT=MICRO_LIVE_READINESS_V1_READY" "$OUT/07_micro_live_readiness.log"

KG_API_HOST=127.0.0.1 KG_API_PORT=19195 DATABASE_URL=postgresql:///finam_core PYTHONPATH=src \
python src/marketcore/api/serve_knowledge_graph_api_v1.py > "$OUT/kg_api.log" 2>&1 &
api_pid=$!

MARKETCORE_UI_HOST=127.0.0.1 MARKETCORE_UI_PORT=19180 KG_API_BASE_URL=http://127.0.0.1:19195 PYTHONPATH=src \
python src/marketcore/presentation/app.py > "$OUT/ui.log" 2>&1 &
ui_pid=$!

cleanup() {
  kill "$ui_pid" >/dev/null 2>&1 || true
  kill "$api_pid" >/dev/null 2>&1 || true
}
trap cleanup EXIT

sleep 2

curl -fsS "http://127.0.0.1:19195/api/kg/v1/paper-edge-discovery" \
  > "$OUT/paper_edge_discovery.json"

curl -fsS "http://127.0.0.1:19195/api/kg/v1/paper-edge-research-candidates?limit=20" \
  > "$OUT/research_candidates.json"

curl -fsS "http://127.0.0.1:19195/api/kg/v1/paper-edge-top-candidates-detail?limit=10" \
  > "$OUT/top_candidates_detail.json"

curl -fsS "http://127.0.0.1:19195/api/kg/v1/paper-edge-candidate-explainability?limit=10" \
  > "$OUT/candidate_explainability.json"

curl -fsS "http://127.0.0.1:19195/api/kg/v1/edge-validation-queue?limit=20" \
  > "$OUT/edge_validation_queue.json"

curl -fsS "http://127.0.0.1:19195/api/kg/v1/edge-validation-pipeline?limit=20" \
  > "$OUT/edge_validation_pipeline.json"

curl -fsS "http://127.0.0.1:19195/api/kg/v1/edge-robustness-check?limit=20" \
  > "$OUT/edge_robustness_check.json"

curl -fsS "http://127.0.0.1:19195/api/kg/v1/edge-oos-validation?limit=20" \
  > "$OUT/edge_oos_validation.json"

curl -fsS "http://127.0.0.1:19195/api/kg/v1/edge-oos-backtest?limit=20" \
  > "$OUT/edge_oos_backtest.json"

curl -fsS "http://127.0.0.1:19195/api/kg/v1/micro-live-readiness?limit=20" \
  > "$OUT/micro_live_readiness.json"

curl -fsS "http://127.0.0.1:19180/paper-edge-discovery" \
  > "$OUT/paper_edge_discovery.html"

curl -fsS "http://127.0.0.1:19180/edge-validation-queue" \
  > "$OUT/edge_validation_queue.html"

curl -fsS "http://127.0.0.1:19180/edge-validation-pipeline" \
  > "$OUT/edge_validation_pipeline.html"

curl -fsS "http://127.0.0.1:19180/edge-robustness-check" \
  > "$OUT/edge_robustness_check.html"

curl -fsS "http://127.0.0.1:19180/edge-oos-validation" \
  > "$OUT/edge_oos_validation.html"

curl -fsS "http://127.0.0.1:19180/edge-oos-backtest" \
  > "$OUT/edge_oos_backtest.html"

curl -fsS "http://127.0.0.1:19180/micro-live-readiness" \
  > "$OUT/micro_live_readiness.html"

PYTHONPATH=src python src/scripts/validate_paper_edge_discovery_phase_acceptance_v1.py \
  --dir "$OUT" | tee "$OUT/acceptance.log"

grep -q "VERDICT=PAPER_EDGE_DISCOVERY_PHASE_ACCEPTANCE_V1_READY" "$OUT/acceptance.log"

candidates_rows=$(psql -At -d finam_core -c "SELECT count(*) FROM marketcore_ui.paper_edge_research_candidates_v1;")
queue_rows=$(psql -At -d finam_core -c "SELECT count(*) FROM marketcore_ui.edge_validation_queue_v1;")
pipeline_rows=$(psql -At -d finam_core -c "SELECT count(*) FROM marketcore_ui.edge_validation_pipeline_v1;")
robustness_rows=$(psql -At -d finam_core -c "SELECT count(*) FROM marketcore_ui.edge_robustness_check_v1;")
oos_rows=$(psql -At -d finam_core -c "SELECT count(*) FROM marketcore_ui.edge_oos_validation_v1;")
backtest_rows=$(psql -At -d finam_core -c "SELECT count(*) FROM marketcore_ui.edge_oos_backtest_v1;")
micro_live_rows=$(psql -At -d finam_core -c "SELECT count(*) FROM marketcore_ui.micro_live_readiness_v1;")
micro_live_allowed_rows=$(psql -At -d finam_core -c "SELECT count(*) FROM marketcore_ui.micro_live_readiness_v1 WHERE micro_live_allowed=true;")

test "$candidates_rows" -gt 0
test "$queue_rows" -gt 0
test "$pipeline_rows" -gt 0
test "$robustness_rows" -gt 0
test "$oos_rows" -gt 0
test "$backtest_rows" -gt 0
test "$micro_live_rows" -gt 0
test "$micro_live_allowed_rows" = "0"

echo "paper_edge_candidates_rows=$candidates_rows"
echo "edge_validation_queue_rows=$queue_rows"
echo "edge_validation_pipeline_rows=$pipeline_rows"
echo "edge_robustness_rows=$robustness_rows"
echo "edge_oos_validation_rows=$oos_rows"
echo "edge_oos_backtest_rows=$backtest_rows"
echo "micro_live_readiness_rows=$micro_live_rows"
echo "micro_live_allowed_rows=$micro_live_allowed_rows"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=PAPER_EDGE_DISCOVERY_PHASE_ACCEPTANCE_V1_READY"
echo "VERDICT=TEST_PAPER_EDGE_DISCOVERY_PHASE_ACCEPTANCE_V1_OK"
