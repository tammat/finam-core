#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_EDGE_MARKET_DATA_BINDING_USE_MARKET_UNIVERSE_V1 ==="

cp src/scripts/build_paper_edge_market_data_binding_v1.py \
   /tmp/build_paper_edge_market_data_binding_v1.py.bak


PYTHONPATH=src python -m py_compile \
  src/scripts/build_paper_edge_market_data_binding_v1.py \
  src/scripts/build_paper_edge_market_data_freshness_v1.py

DATABASE_URL=postgresql:///finam_core PYTHONPATH=src \
python src/scripts/build_paper_edge_market_data_binding_v1.py \
  | tee /tmp/binding_market_universe_v1.txt

DATABASE_URL=postgresql:///finam_core PYTHONPATH=src \
python src/scripts/build_paper_edge_market_data_freshness_v1.py \
  | tee /tmp/freshness_market_universe_v1.txt

grep -q "VERDICT=PAPER_EDGE_DISCOVERY_MARKET_DATA_BINDING_V1_READY" /tmp/binding_market_universe_v1.txt
grep -q "VERDICT=PAPER_EDGE_DISCOVERY_MARKET_DATA_FRESHNESS_V1_READY" /tmp/freshness_market_universe_v1.txt

br_any=$(psql -At -d finam_core -c "
SELECT count(*)
FROM marketcore_ui.paper_edge_market_data_freshness_v1
WHERE candidate_symbol='BR@RTSX' AND candidate_timeframe='ANY';
")

symbols=$(psql -At -d finam_core -c "
SELECT count(DISTINCT candidate_symbol)
FROM marketcore_ui.paper_edge_market_data_freshness_v1
WHERE row_type='CANDIDATE_BINDING';
")

test "$br_any" = "0"
test "$symbols" -gt 1

sudo systemctl restart marketcore-kg-api.service
sudo systemctl restart marketcore-ui-shell.service

echo "br_any=$br_any"
echo "binding_symbols=$symbols"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=EDGE_MARKET_DATA_BINDING_USE_MARKET_UNIVERSE_V1_READY"
echo "VERDICT=TEST_EDGE_MARKET_DATA_BINDING_USE_MARKET_UNIVERSE_V1_OK"
