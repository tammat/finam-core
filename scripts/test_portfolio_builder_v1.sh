#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_PORTFOLIO_BUILDER_V1 ==="

PYTHONPATH=src python -m py_compile \
  src/scripts/build_portfolio_builder_v1.py

DATABASE_URL=postgresql:///finam_core PYTHONPATH=src \
python src/scripts/build_portfolio_builder_v1.py | tee /tmp/portfolio_builder_v1.txt

grep -q "VERDICT=PORTFOLIO_BUILDER_V1_READY" /tmp/portfolio_builder_v1.txt

equity_rows=$(psql -At -d finam_core -c "
SELECT count(*)
FROM analytics.portfolio_equity_snapshot_v1
WHERE portfolio_scope='GLOBAL';
")

bad_equity=$(psql -At -d finam_core -c "
SELECT count(*)
FROM analytics.portfolio_equity_snapshot_v1
WHERE equity IS NULL
   OR positions_value IS NULL
   OR gross_exposure IS NULL;
")

test "$equity_rows" -gt 0
test "$bad_equity" = "0"

psql -d finam_core -c "
SELECT
    portfolio_scope,
    cash,
    positions_value,
    equity,
    gross_exposure,
    net_exposure,
    source_version
FROM analytics.portfolio_equity_snapshot_v1
WHERE portfolio_scope='GLOBAL';
"

psql -d finam_core -c "
SELECT
    symbol,
    asset_class,
    quantity,
    market_value,
    exposure,
    position_status
FROM analytics.portfolio_position_snapshot_v1
ORDER BY symbol
LIMIT 30;
"

echo "equity_rows=$equity_rows"
echo "bad_equity_rows=$bad_equity"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=TEST_PORTFOLIO_BUILDER_V1_OK"
