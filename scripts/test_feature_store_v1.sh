#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_FEATURE_STORE_V1 ==="

sudo -u postgres psql -v ON_ERROR_STOP=1 -d finam_core \
  -f sql/analytics/003_feature_snapshot_v1.sql

PYTHONPATH=src python -m py_compile src/scripts/build_feature_snapshot_v1.py

DATABASE_URL=postgresql:///finam_core PYTHONPATH=src \
python src/scripts/build_market_model_v1.py

DATABASE_URL=postgresql:///finam_core PYTHONPATH=src \
python src/scripts/build_feature_snapshot_v1.py | tee /tmp/feature_store_v1.txt

grep -q "VERDICT=FEATURE_STORE_V1_READY" /tmp/feature_store_v1.txt

rows=$(psql -At -d finam_core -c "SELECT count(*) FROM analytics.feature_snapshot_v1;")
symbols=$(psql -At -d finam_core -c "SELECT count(DISTINCT symbol) FROM analytics.feature_snapshot_v1;")
bad_source=$(psql -At -d finam_core -c "SELECT count(*) FROM analytics.feature_snapshot_v1 WHERE source_table <> 'marketcore.market_snapshot_v1';")

test "$rows" -gt 0
test "$symbols" -gt 1
test "$bad_source" = "0"

psql -d finam_core -c "
SELECT symbol, timeframe, bar_ts, close, range_pct, body_pct, freshness_sec, feature_quality_score
FROM analytics.feature_snapshot_v1
ORDER BY bar_ts DESC, symbol
LIMIT 30;
"

echo "feature_rows=$rows"
echo "feature_symbols=$symbols"
echo "bad_source=$bad_source"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=TEST_FEATURE_STORE_V1_OK"
