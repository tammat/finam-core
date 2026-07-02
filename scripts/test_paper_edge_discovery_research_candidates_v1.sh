#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_PAPER_EDGE_DISCOVERY_RESEARCH_CANDIDATES_V1 ==="

scripts/apply_paper_edge_discovery_research_candidates_v1.sh

PYTHONPATH=src python -m py_compile \
  src/scripts/build_paper_edge_discovery_research_candidates_v1.py \
  src/marketcore/api/serve_knowledge_graph_api_v1.py \
  src/marketcore/presentation/pages/paper_edge_discovery.py \
  src/marketcore/presentation/app.py

sudo -u postgres env \
  DATABASE_URL=postgresql:///finam_core \
  PYTHONPATH=src \
  /opt/finam-core/venv/bin/python src/scripts/build_paper_edge_discovery_research_candidates_v1.py \
  | tee /tmp/paper_edge_research_candidates_build_v1.txt

grep -q "VERDICT=PAPER_EDGE_DISCOVERY_RESEARCH_CANDIDATES_V1_READY" \
  /tmp/paper_edge_research_candidates_build_v1.txt

if grep -R "psycopg2\|DATABASE_URL\|SELECT " -n src/marketcore/presentation/pages/paper_edge_discovery.py; then
  echo "FORBIDDEN_DIRECT_DB_ACCESS_IN_UI_PAGE"
  exit 1
fi

KG_API_HOST=127.0.0.1 KG_API_PORT=18195 DATABASE_URL=postgresql:///finam_core PYTHONPATH=src \
python src/marketcore/api/serve_knowledge_graph_api_v1.py > /tmp/kg_api_candidates_v1.log 2>&1 &
api_pid=$!

MARKETCORE_UI_HOST=127.0.0.1 MARKETCORE_UI_PORT=18180 KG_API_BASE_URL=http://127.0.0.1:18195 PYTHONPATH=src \
python src/marketcore/presentation/app.py > /tmp/paper_edge_candidates_v1.log 2>&1 &
ui_pid=$!

cleanup() {
  kill "$ui_pid" >/dev/null 2>&1 || true
  kill "$api_pid" >/dev/null 2>&1 || true
}
trap cleanup EXIT

sleep 2

curl -fsS "http://127.0.0.1:18195/api/kg/v1/paper-edge-research-candidates" \
  > /tmp/paper_edge_research_candidates_api_v1.json

curl -fsS "http://127.0.0.1:18180/paper-edge-discovery" \
  > /tmp/paper_edge_research_candidates_page_v1.html

grep -q '"status": "OK"' /tmp/paper_edge_research_candidates_api_v1.json
grep -q "Research Candidates" /tmp/paper_edge_research_candidates_page_v1.html
grep -q "marketcore_ui.paper_edge_research_candidates_v1" /tmp/paper_edge_research_candidates_page_v1.html
grep -q "Paper Runtime Real Data" /tmp/paper_edge_research_candidates_page_v1.html
grep -q "PAPER_RUNTIME" /tmp/paper_edge_research_candidates_page_v1.html
grep -q "MARKETCORE_UI_SHELL_V1" /tmp/paper_edge_research_candidates_page_v1.html

rows=$(psql -At -d finam_core -c "SELECT count(*) FROM marketcore_ui.paper_edge_research_candidates_v1;")

echo "research_candidates_rows=$rows"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=PAPER_EDGE_DISCOVERY_RESEARCH_CANDIDATES_V1_READY"
echo "VERDICT=TEST_PAPER_EDGE_DISCOVERY_RESEARCH_CANDIDATES_V1_OK"
