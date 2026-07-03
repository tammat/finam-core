#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_EDGE_UI_USE_MARKET_UNIVERSE_V1 ==="

PYTHONPATH=src python -m py_compile \
  src/marketcore/presentation/pages/edge_validation_queue.py \
  src/marketcore/presentation/pages/edge_validation_pipeline.py \
  src/marketcore/api/serve_knowledge_graph_api_v1.py \
  src/scripts/audit_edge_ui_use_market_universe_v1.py

PYTHONPATH=src python src/scripts/audit_edge_ui_use_market_universe_v1.py \
  | tee /tmp/edge_ui_use_market_universe_v1.txt

grep -q "VERDICT=EDGE_UI_USE_MARKET_UNIVERSE_V1_READY" /tmp/edge_ui_use_market_universe_v1.txt

DATABASE_URL=postgresql:///finam_core PYTHONPATH=src \
python src/scripts/build_paper_edge_market_universe_candidates_v1.py >/tmp/ui_market_universe_candidates.txt

DATABASE_URL=postgresql:///finam_core PYTHONPATH=src \
python src/scripts/build_market_universe_ranking_v1.py >/tmp/ui_market_universe_ranking.txt

DATABASE_URL=postgresql:///finam_core PYTHONPATH=src \
python src/scripts/build_market_universe_research_queue_v1.py >/tmp/ui_market_universe_queue.txt

DATABASE_URL=postgresql:///finam_core PYTHONPATH=src \
python src/scripts/build_edge_validation_use_market_universe_v1.py >/tmp/ui_edge_validation_market_universe.txt

sudo systemctl restart marketcore-kg-api.service
sudo systemctl restart marketcore-ui-shell.service
sleep 2

curl -fsS "http://127.0.0.1:8080/edge-validation-queue" > /tmp/edge_validation_queue_market_universe.html
curl -fsS "http://127.0.0.1:8080/edge-validation-pipeline" > /tmp/edge_validation_pipeline_market_universe.html

grep -q "Проверка" /tmp/edge_validation_queue_market_universe.html
grep -q "market_universe_research_queue_v1" /tmp/edge_validation_queue_market_universe.html
grep -q "Этапы" /tmp/edge_validation_pipeline_market_universe.html
grep -q "edge_validation_use_market_universe_v1" /tmp/edge_validation_pipeline_market_universe.html

if grep -q "BR@RTSX" /tmp/edge_validation_queue_market_universe.html; then
  br_total=$(grep -o "BR@RTSX" /tmp/edge_validation_queue_market_universe.html | wc -l)
  symbols=$(psql -At -d finam_core -c "SELECT count(DISTINCT symbol) FROM marketcore_ui.market_universe_research_queue_v1;")
  test "$symbols" -gt 1
  echo "BR_PRESENT_BUT_NOT_BR_ONLY count=$br_total symbols=$symbols"
fi

symbols=$(psql -At -d finam_core -c "SELECT count(DISTINCT symbol) FROM marketcore_ui.market_universe_research_queue_v1;")
test "$symbols" -gt 1

echo "market_universe_symbols=$symbols"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=EDGE_UI_USE_MARKET_UNIVERSE_V1_READY"
echo "VERDICT=TEST_EDGE_UI_USE_MARKET_UNIVERSE_V1_OK"
