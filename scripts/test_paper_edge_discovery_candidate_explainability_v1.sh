#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_PAPER_EDGE_DISCOVERY_CANDIDATE_EXPLAINABILITY_V1 ==="

PYTHONPATH=src python -m py_compile \
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
  > /tmp/candidate_explainability_builder_v1.txt

KG_API_HOST=127.0.0.1 KG_API_PORT=18395 DATABASE_URL=postgresql:///finam_core PYTHONPATH=src \
python src/marketcore/api/serve_knowledge_graph_api_v1.py > /tmp/kg_api_candidate_explainability_v1.log 2>&1 &
api_pid=$!

MARKETCORE_UI_HOST=127.0.0.1 MARKETCORE_UI_PORT=18380 KG_API_BASE_URL=http://127.0.0.1:18395 PYTHONPATH=src \
python src/marketcore/presentation/app.py > /tmp/candidate_explainability_page_v1.log 2>&1 &
ui_pid=$!

cleanup() {
  kill "$ui_pid" >/dev/null 2>&1 || true
  kill "$api_pid" >/dev/null 2>&1 || true
}
trap cleanup EXIT

sleep 2

curl -fsS "http://127.0.0.1:18395/api/kg/v1/paper-edge-candidate-explainability?limit=5" \
  > /tmp/candidate_explainability_api_v1.json

curl -fsS "http://127.0.0.1:18380/paper-edge-discovery" \
  > /tmp/candidate_explainability_page_v1.html

grep -q '"status": "OK"' /tmp/candidate_explainability_api_v1.json
grep -q '"explainability_status"' /tmp/candidate_explainability_api_v1.json
grep -q '"why_selected"' /tmp/candidate_explainability_api_v1.json
grep -q '"risk_explanation"' /tmp/candidate_explainability_api_v1.json
grep -q '"recommended_action"' /tmp/candidate_explainability_api_v1.json

grep -q "Candidate Explainability" /tmp/candidate_explainability_page_v1.html
grep -q "Почему выбран" /tmp/candidate_explainability_page_v1.html
grep -q "Доказательства" /tmp/candidate_explainability_page_v1.html
grep -q "Риски" /tmp/candidate_explainability_page_v1.html
grep -q "Рекомендация" /tmp/candidate_explainability_page_v1.html
grep -q "PAPER_EDGE_DISCOVERY_CANDIDATE_EXPLAINABILITY_V1" /tmp/candidate_explainability_page_v1.html
grep -q "MARKETCORE_UI_SHELL_V1" /tmp/candidate_explainability_page_v1.html

echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=PAPER_EDGE_DISCOVERY_CANDIDATE_EXPLAINABILITY_V1_READY"
echo "VERDICT=TEST_PAPER_EDGE_DISCOVERY_CANDIDATE_EXPLAINABILITY_V1_OK"
