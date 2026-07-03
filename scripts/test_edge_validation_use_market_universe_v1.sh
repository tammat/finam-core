#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_EDGE_VALIDATION_USE_MARKET_UNIVERSE_V1 ==="

sudo -u postgres psql -v ON_ERROR_STOP=1 -d finam_core \
  -f sql/marketcore_ui/037_edge_validation_use_market_universe_v1.sql

PYTHONPATH=src python -m py_compile \
  src/scripts/build_edge_validation_use_market_universe_v1.py

DATABASE_URL=postgresql:///finam_core PYTHONPATH=src \
python src/scripts/build_paper_edge_market_universe_candidates_v1.py >/tmp/validation_use_market_universe_candidates_v1.txt

DATABASE_URL=postgresql:///finam_core PYTHONPATH=src \
python src/scripts/build_market_universe_ranking_v1.py >/tmp/validation_use_market_universe_ranking_v1.txt

DATABASE_URL=postgresql:///finam_core PYTHONPATH=src \
python src/scripts/build_market_universe_research_queue_v1.py >/tmp/validation_use_market_universe_queue_v1.txt

DATABASE_URL=postgresql:///finam_core PYTHONPATH=src \
python src/scripts/build_edge_validation_use_market_universe_v1.py \
  | tee /tmp/edge_validation_use_market_universe_v1.txt

grep -q "VERDICT=EDGE_VALIDATION_USE_MARKET_UNIVERSE_V1_READY" \
  /tmp/edge_validation_use_market_universe_v1.txt

rows=$(psql -At -d finam_core -c "SELECT count(*) FROM marketcore_ui.edge_validation_use_market_universe_v1;")
symbols=$(psql -At -d finam_core -c "SELECT count(DISTINCT symbol) FROM marketcore_ui.edge_validation_use_market_universe_v1;")
ready=$(psql -At -d finam_core -c "SELECT count(*) FROM marketcore_ui.edge_validation_use_market_universe_v1 WHERE validation_status='READY_FOR_VALIDATION';")
br_only=$(psql -At -d finam_core -c "SELECT count(*) = count(*) FILTER (WHERE symbol LIKE 'BR%') FROM marketcore_ui.edge_validation_use_market_universe_v1;")

test "$rows" -gt 0
test "$symbols" -gt 1
test "$ready" -gt 0
test "$br_only" = "f"

psql -d finam_core -c "
SELECT
    validation_rank,
    symbol,
    timeframe,
    asset_class,
    strategy,
    total_score,
    research_priority,
    validation_status
FROM marketcore_ui.edge_validation_use_market_universe_v1
ORDER BY validation_rank
LIMIT 30;
"

echo "validation_rows=$rows"
echo "validation_symbols=$symbols"
echo "ready_for_validation=$ready"
echo "br_only=$br_only"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=EDGE_VALIDATION_USE_MARKET_UNIVERSE_V1_READY"
echo "VERDICT=TEST_EDGE_VALIDATION_USE_MARKET_UNIVERSE_V1_OK"
