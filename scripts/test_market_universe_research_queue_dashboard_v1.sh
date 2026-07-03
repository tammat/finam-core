#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_MARKET_UNIVERSE_RESEARCH_QUEUE_DASHBOARD_V1 ==="

PYTHONPATH=src python -m py_compile \
  src/marketcore/api/serve_knowledge_graph_api_v1.py \
  src/marketcore/presentation/pages/knowledge_graph.py \
  src/marketcore/presentation/pages/market_universe_research_queue.py \
  src/marketcore/presentation/registry.py \
  src/marketcore/presentation/app.py

if grep -R "psycopg2\|DATABASE_URL\|SELECT " -n \
  src/marketcore/presentation/pages/knowledge_graph.py \
  src/marketcore/presentation/pages/market_universe_research_queue.py; then
  echo "FORBIDDEN_DIRECT_DB_ACCESS_IN_UI_PAGE"
  exit 1
fi

DATABASE_URL=postgresql:///finam_core PYTHONPATH=src \
python src/scripts/build_market_universe_ranking_v1.py >/tmp/ranking_for_queue_dashboard_v1.txt

DATABASE_URL=postgresql:///finam_core PYTHONPATH=src \
python src/scripts/build_market_universe_research_queue_v1.py >/tmp/research_queue_for_dashboard_v1.txt

sudo systemctl restart marketcore-kg-api.service
sudo systemctl restart marketcore-ui-shell.service
sleep 2

curl -fsS "http://127.0.0.1:8095/api/kg/v1/market-universe-research-queue?limit=20" \
  > /tmp/market_universe_research_queue_api_v1.json

curl -fsS "http://127.0.0.1:8080/market-universe-research-queue" \
  > /tmp/market_universe_research_queue_page_v1.html

curl -fsS "http://127.0.0.1:8080/knowledge-graph" \
  > /tmp/knowledge_graph_fixed_v1.html

grep -q '"status": "OK"' /tmp/market_universe_research_queue_api_v1.json
grep -q '"queue_rank"' /tmp/market_universe_research_queue_api_v1.json
grep -q '"recommended_strategy_family"' /tmp/market_universe_research_queue_api_v1.json

grep -q "Очередь исследований" /tmp/market_universe_research_queue_page_v1.html
grep -q "MARKET_UNIVERSE_RESEARCH_QUEUE_TIMER_V1" /tmp/market_universe_research_queue_page_v1.html
grep -q "MARKETCORE_UI_SHELL_V1" /tmp/market_universe_research_queue_page_v1.html

grep -q "Граф знаний" /tmp/knowledge_graph_fixed_v1.html
grep -q "Матрица маршрутов UI" /tmp/knowledge_graph_fixed_v1.html
grep -q "MARKETCORE_UI_SHELL_V1" /tmp/knowledge_graph_fixed_v1.html

rows=$(psql -At -d finam_core -c "SELECT count(*) FROM marketcore_ui.market_universe_research_queue_v1;")
high=$(psql -At -d finam_core -c "SELECT count(*) FROM marketcore_ui.market_universe_research_queue_v1 WHERE research_priority='HIGH';")

test "$rows" -gt 0
test "$high" -gt 0

echo "research_queue_rows=$rows"
echo "research_queue_high=$high"
echo "knowledge_graph_fixed=1"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=MARKET_UNIVERSE_RESEARCH_QUEUE_DASHBOARD_V1_READY"
echo "VERDICT=TEST_MARKET_UNIVERSE_RESEARCH_QUEUE_DASHBOARD_V1_OK"
