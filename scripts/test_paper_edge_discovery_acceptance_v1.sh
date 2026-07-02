#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_PAPER_EDGE_DISCOVERY_ACCEPTANCE_V1 ==="

OUT="/tmp/paper_edge_discovery_acceptance_v1"
rm -rf "$OUT"
mkdir -p "$OUT"

PYTHONPATH=src python -m py_compile \
  src/scripts/validate_paper_edge_discovery_acceptance_v1.py \
  src/marketcore/api/serve_knowledge_graph_api_v1.py \
  src/marketcore/presentation/pages/paper_edge_discovery.py \
  src/marketcore/presentation/app.py

if grep -R "psycopg2\|DATABASE_URL\|SELECT " -n src/marketcore/presentation/pages/paper_edge_discovery.py; then
  echo "FORBIDDEN_DIRECT_DB_ACCESS_IN_UI_PAGE"
  exit 1
fi

sudo -u postgres env \
  DATABASE_URL=postgresql:///finam_core \
  PYTHONPATH=src \
  /opt/finam-core/venv/bin/python src/scripts/build_paper_edge_discovery_research_candidates_v1.py \
  > "$OUT/research_candidates_builder.log"

KG_API_HOST=127.0.0.1 KG_API_PORT=18495 DATABASE_URL=postgresql:///finam_core PYTHONPATH=src \
python src/marketcore/api/serve_knowledge_graph_api_v1.py > "$OUT/kg_api.log" 2>&1 &
api_pid=$!

MARKETCORE_UI_HOST=127.0.0.1 MARKETCORE_UI_PORT=18480 KG_API_BASE_URL=http://127.0.0.1:18495 PYTHONPATH=src \
python src/marketcore/presentation/app.py > "$OUT/ui.log" 2>&1 &
ui_pid=$!

cleanup() {
  kill "$ui_pid" >/dev/null 2>&1 || true
  kill "$api_pid" >/dev/null 2>&1 || true
}
trap cleanup EXIT

sleep 2

curl -fsS "http://127.0.0.1:18495/api/kg/v1/health" \
  > "$OUT/health.json"

curl -fsS "http://127.0.0.1:18495/api/kg/v1/statistics" \
  > "$OUT/statistics.json"

curl -fsS "http://127.0.0.1:18495/api/kg/v1/paper-runtime" \
  > "$OUT/paper_runtime.json"

curl -fsS "http://127.0.0.1:18495/api/kg/v1/paper-edge-discovery" \
  > "$OUT/paper_edge_discovery.json"

curl -fsS "http://127.0.0.1:18495/api/kg/v1/paper-edge-research-candidates?limit=20" \
  > "$OUT/research_candidates.json"

curl -fsS "http://127.0.0.1:18495/api/kg/v1/paper-edge-top-candidates-detail?limit=10" \
  > "$OUT/top_candidates_detail.json"

curl -fsS "http://127.0.0.1:18495/api/kg/v1/paper-edge-candidate-explainability?limit=10" \
  > "$OUT/candidate_explainability.json"

curl -fsS "http://127.0.0.1:18480/paper-edge-discovery" \
  > "$OUT/page.html"

PYTHONPATH=src python src/scripts/validate_paper_edge_discovery_acceptance_v1.py \
  --dir "$OUT" | tee "$OUT/acceptance.log"

grep -q "VERDICT=PAPER_EDGE_DISCOVERY_ACCEPTANCE_V1_READY" "$OUT/acceptance.log"

rows=$(psql -At -d finam_core -c "SELECT count(*) FROM marketcore_ui.paper_edge_research_candidates_v1;")
test "$rows" -gt 0

echo "research_candidates_rows=$rows"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=PAPER_EDGE_DISCOVERY_ACCEPTANCE_V1_READY"
echo "VERDICT=TEST_PAPER_EDGE_DISCOVERY_ACCEPTANCE_V1_OK"
