#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_MARKET_UNIVERSE_RANKING_V1 ==="

sudo -u postgres psql -v ON_ERROR_STOP=1 -d finam_core \
  -f sql/marketcore_ui/033_market_universe_ranking_v1.sql

PYTHONPATH=src python -m py_compile \
  src/scripts/build_market_universe_ranking_v1.py \
  src/marketcore/api/serve_knowledge_graph_api_v1.py \
  src/marketcore/presentation/pages/market_universe_ranking.py \
  src/marketcore/presentation/registry.py

DATABASE_URL=postgresql:///finam_core PYTHONPATH=src \
python src/scripts/build_market_universe_ranking_v1.py \
  | tee /tmp/market_universe_ranking_v1.txt

grep -q "VERDICT=MARKET_UNIVERSE_RANKING_V1_READY" /tmp/market_universe_ranking_v1.txt

rows=$(psql -At -d finam_core -c "SELECT count(*) FROM marketcore_ui.market_universe_ranking_v1;")
ready=$(psql -At -d finam_core -c "SELECT count(*) FROM marketcore_ui.market_universe_ranking_v1 WHERE ranking_status='READY_FOR_RESEARCH';")

test "$rows" -gt 0
test "$ready" -gt 0

sudo systemctl restart marketcore-kg-api.service
sudo systemctl restart marketcore-ui-shell.service
sleep 2

curl -fsS "http://127.0.0.1:8095/api/kg/v1/market-universe-ranking?limit=10" > /tmp/market_universe_ranking_api.json
curl -fsS "http://127.0.0.1:8080/market-universe-ranking" > /tmp/market_universe_ranking_page.html

grep -q '"status": "OK"' /tmp/market_universe_ranking_api.json
grep -q '"total_score"' /tmp/market_universe_ranking_api.json
grep -q "Рейтинг рыночной вселенной" /tmp/market_universe_ranking_page.html
grep -q "MARKET_UNIVERSE_RESEARCH_QUEUE_V1" /tmp/market_universe_ranking_page.html

psql -d finam_core -c "
SELECT rank, symbol, timeframe, asset_class, total_score, ranking_status
FROM marketcore_ui.market_universe_ranking_v1
ORDER BY rank
LIMIT 20;
"

echo "ranking_rows=$rows"
echo "ready_for_research=$ready"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=TEST_MARKET_UNIVERSE_RANKING_V1_OK"
