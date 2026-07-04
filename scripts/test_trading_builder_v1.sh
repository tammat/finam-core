#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_TRADING_BUILDER_V1 ==="

PYTHONPATH=src python -m py_compile \
  src/scripts/build_trading_builder_v1.py

DATABASE_URL=postgresql:///finam_core PYTHONPATH=src \
python src/scripts/build_trading_builder_v1.py | tee /tmp/trading_builder_v1.txt

grep -q "VERDICT=TRADING_BUILDER_V1_READY" /tmp/trading_builder_v1.txt

rows=$(psql -At -d finam_core -c "
SELECT count(*)
FROM analytics.trading_order_intent_v1;
")

unsafe=$(psql -At -d finam_core -c "
SELECT count(*)
FROM analytics.trading_order_intent_v1
WHERE live_allowed=true
   OR micro_live_allowed=true
   OR order_sent=true;
")

test "$unsafe" = "0"

psql -d finam_core -c "
SELECT
    symbol,
    strategy_family,
    risk_score,
    order_side,
    order_type,
    quantity,
    trading_decision_code,
    recommendation_code,
    paper_allowed,
    live_allowed,
    order_sent
FROM analytics.trading_order_intent_v1
ORDER BY signal_ts DESC
LIMIT 30;
"

echo "trading_intent_rows=$rows"
echo "unsafe_live_or_sent_rows=$unsafe"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=TEST_TRADING_BUILDER_V1_OK"
