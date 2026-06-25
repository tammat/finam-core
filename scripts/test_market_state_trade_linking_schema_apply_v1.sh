#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core || exit 1

echo "=== TEST_MARKET_STATE_TRADE_LINKING_SCHEMA_APPLY_V1 ==="

python3 -m py_compile \
src/scripts/research/apply_market_state_trade_linking_schema_v1.py

DATABASE_URL=${DATABASE_URL} \
src/scripts/research/apply_market_state_trade_linking_schema_v1.py --apply \
| tee /tmp/trade_linking_schema_apply.out

grep -q "MARKET_STATE_TRADE_LINKING_SCHEMA_APPLY_OK" \
/tmp/trade_linking_schema_apply.out

grep -q "tables_applied=1" \
/tmp/trade_linking_schema_apply.out

grep -q "indexes_applied=4" \
/tmp/trade_linking_schema_apply.out

echo "TEST_MARKET_STATE_TRADE_LINKING_SCHEMA_APPLY_V1_OK"
