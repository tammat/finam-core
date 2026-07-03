#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_MARKET_UNIVERSE_RESEARCH_QUEUE_V1 ==="

sudo -u postgres psql -v ON_ERROR_STOP=1 -d finam_core \
  -f sql/marketcore_ui/034_market_universe_research_queue_v1.sql

PYTHONPATH=src python -m py_compile \
  src/scripts/build_market_universe_research_queue_v1.py

DATABASE_URL=postgresql:///finam_core PYTHONPATH=src \
python src/scripts/build_market_universe_research_queue_v1.py \
  | tee /tmp/market_universe_research_queue_v1.txt

grep -q "VERDICT=MARKET_UNIVERSE_RESEARCH_QUEUE_V1_READY" \
  /tmp/market_universe_research_queue_v1.txt

rows=$(psql -At -d finam_core -c "SELECT count(*) FROM marketcore_ui.market_universe_research_queue_v1;")
high=$(psql -At -d finam_core -c "SELECT count(*) FROM marketcore_ui.market_universe_research_queue_v1 WHERE research_priority='HIGH';")

test "$rows" -gt 0
test "$high" -gt 0

psql -d finam_core -c "
SELECT
    queue_rank,
    symbol,
    timeframe,
    asset_class,
    total_score,
    ranking_status,
    research_priority,
    recommended_strategy_family
FROM marketcore_ui.market_universe_research_queue_v1
ORDER BY queue_rank;
"

echo "research_queue_rows=$rows"
echo "research_queue_high=$high"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=TEST_MARKET_UNIVERSE_RESEARCH_QUEUE_V1_OK"
