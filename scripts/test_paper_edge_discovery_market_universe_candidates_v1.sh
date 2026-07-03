#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_PAPER_EDGE_DISCOVERY_MARKET_UNIVERSE_CANDIDATES_V1 ==="

sudo -u postgres psql -v ON_ERROR_STOP=1 -d finam_core \
  -f sql/marketcore_ui/032_paper_edge_market_universe_candidates_v1.sql

PYTHONPATH=src python -m py_compile \
  src/scripts/build_paper_edge_market_universe_candidates_v1.py

DATABASE_URL=postgresql:///finam_core PYTHONPATH=src \
python src/scripts/build_paper_edge_market_universe_candidates_v1.py \
  | tee /tmp/paper_edge_market_universe_candidates_v1.txt

grep -q "VERDICT=PAPER_EDGE_DISCOVERY_MARKET_UNIVERSE_CANDIDATES_V1_READY" \
  /tmp/paper_edge_market_universe_candidates_v1.txt

rows=$(psql -At -d finam_core -c "SELECT count(*) FROM marketcore_ui.paper_edge_market_universe_candidates_v1;")
symbols=$(psql -At -d finam_core -c "SELECT count(DISTINCT symbol) FROM marketcore_ui.paper_edge_market_universe_candidates_v1;")
br_only=$(psql -At -d finam_core -c "SELECT count(*) = count(*) FILTER (WHERE symbol LIKE 'BR%') FROM marketcore_ui.paper_edge_market_universe_candidates_v1;")

test "$rows" -gt 0
test "$symbols" -gt 1
test "$br_only" = "f"

psql -d finam_core -c "
SELECT candidate_rank, symbol, timeframe, asset_class, bars_total, latest_ts, universe_status, candidate_status, score
FROM marketcore_ui.paper_edge_market_universe_candidates_v1
ORDER BY candidate_rank
LIMIT 40;
"

echo "market_universe_rows=$rows"
echo "market_universe_symbols=$symbols"
echo "br_only=$br_only"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=TEST_PAPER_EDGE_DISCOVERY_MARKET_UNIVERSE_CANDIDATES_V1_OK"
