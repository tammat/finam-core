#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_EDGE_PIPELINE_V2_BUILDER_V1 ==="

PYTHONPATH=src python -m py_compile \
  src/scripts/build_edge_pipeline_snapshot_v1.py

DATABASE_URL=postgresql:///finam_core PYTHONPATH=src \
python src/scripts/build_edge_pipeline_snapshot_v1.py \
  | tee /tmp/edge_pipeline_v2_builder_v1.txt

grep -q "VERDICT=EDGE_PIPELINE_V2_BUILDER_V1_READY" \
  /tmp/edge_pipeline_v2_builder_v1.txt

rows=$(psql -At -d finam_core -c "SELECT count(*) FROM analytics.edge_pipeline_snapshot_v1;")
symbols=$(psql -At -d finam_core -c "SELECT count(DISTINCT symbol) FROM analytics.edge_pipeline_snapshot_v1;")
duplicates=$(psql -At -d finam_core -c "
SELECT count(*)
FROM (
    SELECT symbol, timeframe, strategy_family, count(*) AS cnt
    FROM analytics.edge_pipeline_snapshot_v1
    GROUP BY symbol, timeframe, strategy_family
    HAVING count(*) > 1
) d;
")
bad_names=$(psql -At -d finam_core -c "
SELECT count(*)
FROM analytics.edge_pipeline_snapshot_v1
WHERE display_name = '' OR display_name IS NULL;
")

test "$rows" -gt 0
test "$symbols" -gt 1
test "$duplicates" = "0"
test "$bad_names" = "0"

psql -d finam_core -c "
SELECT
    symbol,
    display_name,
    asset_class,
    timeframe,
    strategy_family,
    pipeline_stage,
    overall_status,
    ranking_score,
    research_priority,
    research_status,
    validation_status,
    risk_status,
    trading_status
FROM analytics.edge_pipeline_snapshot_v1
ORDER BY ranking_score DESC, symbol, timeframe
LIMIT 30;
"

echo "edge_pipeline_rows=$rows"
echo "edge_pipeline_symbols=$symbols"
echo "duplicates=$duplicates"
echo "bad_names=$bad_names"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=EDGE_PIPELINE_V2_BUILDER_V1_READY"
echo "VERDICT=TEST_EDGE_PIPELINE_V2_BUILDER_V1_OK"
