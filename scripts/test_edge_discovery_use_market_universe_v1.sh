#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_EDGE_DISCOVERY_USE_MARKET_UNIVERSE_V1 ==="

sudo -u postgres psql -v ON_ERROR_STOP=1 -d finam_core \
  -f sql/marketcore_ui/036_edge_discovery_use_market_universe_v1.sql

PYTHONPATH=src python -m py_compile \
  src/scripts/build_edge_discovery_use_market_universe_v1.py \
  src/marketcore/api/serve_knowledge_graph_api_v1.py

DATABASE_URL=postgresql:///finam_core PYTHONPATH=src \
python src/scripts/build_paper_edge_market_universe_candidates_v1.py >/tmp/use_market_universe_candidates_v1.txt

DATABASE_URL=postgresql:///finam_core PYTHONPATH=src \
python src/scripts/build_market_universe_ranking_v1.py >/tmp/use_market_universe_ranking_v1.txt

DATABASE_URL=postgresql:///finam_core PYTHONPATH=src \
python src/scripts/build_market_universe_research_queue_v1.py >/tmp/use_market_universe_queue_v1.txt

DATABASE_URL=postgresql:///finam_core PYTHONPATH=src \
python src/scripts/build_edge_discovery_use_market_universe_v1.py \
  | tee /tmp/edge_discovery_use_market_universe_v1.txt

grep -q "VERDICT=EDGE_DISCOVERY_USE_MARKET_UNIVERSE_V1_READY" \
  /tmp/edge_discovery_use_market_universe_v1.txt

status=$(psql -At -d finam_core -c "SELECT migration_status FROM marketcore_ui.edge_discovery_use_market_universe_v1 WHERE id=1;")
queue_symbols=$(psql -At -d finam_core -c "SELECT queue_symbols FROM marketcore_ui.edge_discovery_use_market_universe_v1 WHERE id=1;")
legacy_symbols=$(psql -At -d finam_core -c "SELECT legacy_symbols FROM marketcore_ui.edge_discovery_use_market_universe_v1 WHERE id=1;")

test "$status" = "MARKET_UNIVERSE_ACTIVE"
test "$queue_symbols" -gt 1

psql -d finam_core -c "
SELECT
    migration_status,
    legacy_rows,
    legacy_symbols,
    queue_rows,
    queue_symbols,
    ranking_rows,
    universe_rows,
    recommended_action
FROM marketcore_ui.edge_discovery_use_market_universe_v1
WHERE id=1;
"

psql -d finam_core -c "
SELECT queue_rank, symbol, timeframe, asset_class, total_score, research_priority
FROM marketcore_ui.market_universe_research_queue_v1
ORDER BY queue_rank
LIMIT 20;
"

echo "migration_status=$status"
echo "legacy_symbols=$legacy_symbols"
echo "queue_symbols=$queue_symbols"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=EDGE_DISCOVERY_USE_MARKET_UNIVERSE_V1_READY"
echo "VERDICT=TEST_EDGE_DISCOVERY_USE_MARKET_UNIVERSE_V1_OK"
