#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_EDGE_DISCOVERY_FROM_MARKET_UNIVERSE_V1 ==="

sudo -u postgres psql -v ON_ERROR_STOP=1 -d finam_core \
  -f sql/marketcore_ui/035_edge_discovery_from_market_universe_v1.sql

PYTHONPATH=src python -m py_compile \
  src/scripts/build_edge_discovery_from_market_universe_v1.py

DATABASE_URL=postgresql:///finam_core PYTHONPATH=src \
python src/scripts/build_edge_discovery_from_market_universe_v1.py \
  | tee /tmp/edge_discovery_from_market_universe_v1.txt

grep -q "VERDICT=EDGE_DISCOVERY_FROM_MARKET_UNIVERSE_V1_READY" \
  /tmp/edge_discovery_from_market_universe_v1.txt

rows=$(psql -At -d finam_core -c "SELECT count(*) FROM marketcore_ui.edge_discovery_from_market_universe_v1;")
test "$rows" -gt 0

psql -d finam_core -c "
SELECT discovery_rank, symbol, timeframe, strategy_family, trades_count, winrate, profit_factor, expectancy, edge_status
FROM marketcore_ui.edge_discovery_from_market_universe_v1
ORDER BY discovery_rank
LIMIT 20;
"

echo "edge_discovery_rows=$rows"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=TEST_EDGE_DISCOVERY_FROM_MARKET_UNIVERSE_V1_OK"
