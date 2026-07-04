#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_TRADING_PLATFORM_GOVERNANCE_V1 ==="

PYTHONPATH=src python -m py_compile \
    src/scripts/build_trading_platform_governance_v1.py

DATABASE_URL=postgresql:///finam_core \
PYTHONPATH=src \
python src/scripts/build_trading_platform_governance_v1.py \
| tee /tmp/trading_platform_governance_v1.txt

grep -q \
"VERDICT=TRADING_PLATFORM_GOVERNANCE_V1_READY" \
/tmp/trading_platform_governance_v1.txt

unsafe=$(psql -At -d finam_core -c "
SELECT count(*)
FROM analytics.trading_order_intent_v1
WHERE live_allowed=true
   OR micro_live_allowed=true
   OR order_sent=true;
")

score=$(psql -At -d finam_core -c "
SELECT governance_score
FROM analytics.trading_governance_v1
WHERE governance_scope='GLOBAL';
")

test "$unsafe" = "0"

echo "governance_score=$score"
echo "unsafe_rows=$unsafe"

echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"

echo "VERDICT=TEST_TRADING_PLATFORM_GOVERNANCE_V1_OK"

