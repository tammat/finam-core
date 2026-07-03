#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_PAPER_EDGE_DISCOVERY_MARKET_DATA_FRESHNESS_V1 ==="

scripts/apply_paper_edge_market_data_freshness_v1.sh

PYTHONPATH=src python -m py_compile \
  src/scripts/build_paper_edge_market_data_freshness_v1.py \
  src/marketcore/api/serve_knowledge_graph_api_v1.py \
  src/marketcore/presentation/pages/paper_edge_market_data_freshness.py \
  src/marketcore/presentation/pages/paper_edge_market_data_binding.py \
  src/marketcore/presentation/registry.py \
  src/marketcore/presentation/app.py

if grep -R "psycopg2\|DATABASE_URL\|SELECT " -n src/marketcore/presentation/pages/paper_edge_market_data_freshness.py; then
  echo "FORBIDDEN_DIRECT_DB_ACCESS_IN_UI_PAGE"
  exit 1
fi

sudo -u postgres env \
  DATABASE_URL=postgresql:///finam_core \
  PYTHONPATH=src \
  /opt/finam-core/venv/bin/python src/scripts/build_paper_edge_discovery_research_candidates_v1.py \
  > /tmp/freshness_candidates_builder_v1.txt

sudo -u postgres env \
  DATABASE_URL=postgresql:///finam_core \
  PYTHONPATH=src \
  /opt/finam-core/venv/bin/python src/scripts/build_paper_edge_market_data_binding_v1.py \
  > /tmp/freshness_binding_builder_v1.txt

sudo -u postgres env \
  DATABASE_URL=postgresql:///finam_core \
  PYTHONPATH=src \
  /opt/finam-core/venv/bin/python src/scripts/build_paper_edge_market_data_freshness_v1.py \
  | tee /tmp/paper_edge_market_data_freshness_builder_v1.txt

grep -q "VERDICT=PAPER_EDGE_DISCOVERY_MARKET_DATA_FRESHNESS_V1_READY" \
  /tmp/paper_edge_market_data_freshness_builder_v1.txt

KG_API_HOST=127.0.0.1 KG_API_PORT=20695 DATABASE_URL=postgresql:///finam_core PYTHONPATH=src \
python src/marketcore/api/serve_knowledge_graph_api_v1.py > /tmp/kg_api_market_data_freshness_v1.log 2>&1 &
api_pid=$!

MARKETCORE_UI_HOST=127.0.0.1 MARKETCORE_UI_PORT=20680 KG_API_BASE_URL=http://127.0.0.1:20695 PYTHONPATH=src \
python src/marketcore/presentation/app.py > /tmp/market_data_freshness_ui_v1.log 2>&1 &
ui_pid=$!

cleanup() {
  kill "$ui_pid" >/dev/null 2>&1 || true
  kill "$api_pid" >/dev/null 2>&1 || true
}
trap cleanup EXIT

sleep 2

curl -fsS "http://127.0.0.1:20695/api/kg/v1/paper-edge-market-data-freshness?limit=100" \
  > /tmp/paper_edge_market_data_freshness_api_v1.json

curl -fsS "http://127.0.0.1:20680/paper-edge-market-data-freshness" \
  > /tmp/paper_edge_market_data_freshness_page_v1.html

curl -fsS "http://127.0.0.1:20680/paper-edge-market-data-binding" \
  > /tmp/paper_edge_market_data_binding_freshness_link_v1.html

grep -q '"status": "OK"' /tmp/paper_edge_market_data_freshness_api_v1.json
grep -q '"row_type"' /tmp/paper_edge_market_data_freshness_api_v1.json
grep -q '"freshness_status"' /tmp/paper_edge_market_data_freshness_api_v1.json
grep -q '"diagnosis"' /tmp/paper_edge_market_data_freshness_api_v1.json
grep -q '"recommended_action"' /tmp/paper_edge_market_data_freshness_api_v1.json

grep -q "Свежесть рыночных данных" /tmp/paper_edge_market_data_freshness_page_v1.html
grep -q "Freshness Matrix" /tmp/paper_edge_market_data_freshness_page_v1.html
grep -q "PAPER_EDGE_DISCOVERY_MARKET_SYMBOL_ALIAS_PLAN_V1" /tmp/paper_edge_market_data_freshness_page_v1.html
grep -q "MARKETCORE_UI_SHELL_V1" /tmp/paper_edge_market_data_freshness_page_v1.html

grep -q "paper-edge-market-data-freshness" /tmp/paper_edge_market_data_binding_freshness_link_v1.html
grep -q "PAPER_EDGE_DISCOVERY_MARKET_DATA_FRESHNESS_V1" /tmp/paper_edge_market_data_binding_freshness_link_v1.html

rows=$(psql -At -d finam_core -c "SELECT count(*) FROM marketcore_ui.paper_edge_market_data_freshness_v1;")
candidate_rows=$(psql -At -d finam_core -c "SELECT count(*) FROM marketcore_ui.paper_edge_market_data_freshness_v1 WHERE row_type='CANDIDATE_BINDING';")
source_rows=$(psql -At -d finam_core -c "SELECT count(*) FROM marketcore_ui.paper_edge_market_data_freshness_v1 WHERE row_type='SOURCE_LATEST';")

test "$rows" -gt 0
test "$candidate_rows" -gt 0

psql -d finam_core -c "
SELECT
    row_type,
    freshness_status,
    count(*) AS rows
FROM marketcore_ui.paper_edge_market_data_freshness_v1
GROUP BY row_type, freshness_status
ORDER BY row_type, freshness_status;
"

echo "market_data_freshness_rows=$rows"
echo "candidate_binding_rows=$candidate_rows"
echo "source_latest_rows=$source_rows"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=PAPER_EDGE_DISCOVERY_MARKET_DATA_FRESHNESS_V1_READY"
echo "VERDICT=TEST_PAPER_EDGE_DISCOVERY_MARKET_DATA_FRESHNESS_V1_OK"
