#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core || exit 1

echo "=== TEST_MARKET_INDEX_STATE_SCHEMA_APPLY_V1 ==="

python3 -m py_compile \
src/scripts/research/apply_market_index_state_schema_v1.py

DATABASE_URL=${DATABASE_URL} \
src/scripts/research/apply_market_index_state_schema_v1.py --apply \
| tee /tmp/market_index_state_schema_apply_v1.out

grep -q "MARKET_INDEX_STATE_SCHEMA_APPLY_OK" \
/tmp/market_index_state_schema_apply_v1.out

grep -q "tables_applied=2" \
/tmp/market_index_state_schema_apply_v1.out

grep -q "indexes_applied=4" \
/tmp/market_index_state_schema_apply_v1.out

echo "TEST_MARKET_INDEX_STATE_SCHEMA_APPLY_V1_OK"
