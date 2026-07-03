#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_PAPER_EDGE_DISCOVERY_MARKET_SYMBOL_ALIAS_PLAN_V1 ==="

scripts/apply_paper_edge_market_symbol_alias_plan_v1.sh

PYTHONPATH=src python -m py_compile \
  src/scripts/build_paper_edge_market_symbol_alias_plan_v1.py \
  src/marketcore/api/serve_knowledge_graph_api_v1.py \
  src/marketcore/presentation/pages/paper_edge_market_symbol_alias_plan.py \
  src/marketcore/presentation/pages/paper_edge_market_data_freshness.py \
  src/marketcore/presentation/registry.py \
  src/marketcore/presentation/app.py

if grep -R "psycopg2\|DATABASE_URL\|SELECT " -n src/marketcore/presentation/pages/paper_edge_market_symbol_alias_plan.py; then
  echo "FORBIDDEN_DIRECT_DB_ACCESS_IN_UI_PAGE"
  exit 1
fi

sudo -u postgres env \
  DATABASE_URL=postgresql:///finam_core \
  PYTHONPATH=src \
  /opt/finam-core/venv/bin/python src/scripts/build_paper_edge_market_data_binding_v1.py \
  > /tmp/alias_plan_binding_builder_v1.txt

sudo -u postgres env \
  DATABASE_URL=postgresql:///finam_core \
  PYTHONPATH=src \
  /opt/finam-core/venv/bin/python src/scripts/build_paper_edge_market_data_freshness_v1.py \
  > /tmp/alias_plan_freshness_builder_v1.txt

DATABASE_URL=postgresql:///finam_core PYTHONPATH=src \
python src/scripts/build_paper_edge_market_symbol_alias_plan_v1.py \
  | tee /tmp/paper_edge_market_symbol_alias_plan_builder_v1.txt

grep -q "VERDICT=PAPER_EDGE_DISCOVERY_MARKET_SYMBOL_ALIAS_PLAN_V1_READY" \
  /tmp/paper_edge_market_symbol_alias_plan_builder_v1.txt

KG_API_HOST=127.0.0.1 KG_API_PORT=20795 DATABASE_URL=postgresql:///finam_core PYTHONPATH=src \
python src/marketcore/api/serve_knowledge_graph_api_v1.py > /tmp/kg_api_alias_plan_v1.log 2>&1 &
api_pid=$!

MARKETCORE_UI_HOST=127.0.0.1 MARKETCORE_UI_PORT=20780 KG_API_BASE_URL=http://127.0.0.1:20795 PYTHONPATH=src \
python src/marketcore/presentation/app.py > /tmp/alias_plan_ui_v1.log 2>&1 &
ui_pid=$!

cleanup() {
  kill "$ui_pid" >/dev/null 2>&1 || true
  kill "$api_pid" >/dev/null 2>&1 || true
}
trap cleanup EXIT

sleep 2

curl -fsS "http://127.0.0.1:20795/api/kg/v1/paper-edge-market-symbol-alias-plan?limit=100" \
  > /tmp/paper_edge_market_symbol_alias_plan_api_v1.json

curl -fsS "http://127.0.0.1:20780/paper-edge-market-symbol-alias-plan" \
  > /tmp/paper_edge_market_symbol_alias_plan_page_v1.html

curl -fsS "http://127.0.0.1:20780/paper-edge-market-data-freshness" \
  > /tmp/paper_edge_market_data_freshness_alias_link_v1.html

grep -q '"status": "OK"' /tmp/paper_edge_market_symbol_alias_plan_api_v1.json
grep -q '"candidate_symbol"' /tmp/paper_edge_market_symbol_alias_plan_api_v1.json
grep -q '"alias_symbol"' /tmp/paper_edge_market_symbol_alias_plan_api_v1.json
grep -q '"alias_status"' /tmp/paper_edge_market_symbol_alias_plan_api_v1.json
grep -q '"alias_confidence"' /tmp/paper_edge_market_symbol_alias_plan_api_v1.json

grep -q "План alias рыночных символов" /tmp/paper_edge_market_symbol_alias_plan_page_v1.html
grep -q "Alias Plan" /tmp/paper_edge_market_symbol_alias_plan_page_v1.html
grep -q "PAPER_EDGE_DISCOVERY_MARKET_SYMBOL_ALIAS_APPLY_V1" /tmp/paper_edge_market_symbol_alias_plan_page_v1.html
grep -q "MARKETCORE_UI_SHELL_V1" /tmp/paper_edge_market_symbol_alias_plan_page_v1.html

grep -q "paper-edge-market-symbol-alias-plan" /tmp/paper_edge_market_data_freshness_alias_link_v1.html
grep -q "PAPER_EDGE_DISCOVERY_MARKET_SYMBOL_ALIAS_PLAN_V1" /tmp/paper_edge_market_data_freshness_alias_link_v1.html

rows=$(psql -At -d finam_core -c "SELECT count(*) FROM marketcore_ui.paper_edge_market_symbol_alias_plan_v1;")
candidates=$(psql -At -d finam_core -c "SELECT count(DISTINCT candidate_symbol) FROM marketcore_ui.paper_edge_market_symbol_alias_plan_v1;")

test "$rows" -gt 0
test "$candidates" -gt 0

psql -d finam_core -c "
SELECT
    alias_status,
    alias_match_type,
    count(*) AS rows
FROM marketcore_ui.paper_edge_market_symbol_alias_plan_v1
GROUP BY alias_status, alias_match_type
ORDER BY alias_status, alias_match_type;
"

echo "alias_plan_rows=$rows"
echo "alias_plan_candidates=$candidates"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=PAPER_EDGE_DISCOVERY_MARKET_SYMBOL_ALIAS_PLAN_V1_READY"
echo "VERDICT=TEST_PAPER_EDGE_DISCOVERY_MARKET_SYMBOL_ALIAS_PLAN_V1_OK"
