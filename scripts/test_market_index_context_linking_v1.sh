#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core || exit 1

echo "=== TEST_MARKET_INDEX_CONTEXT_LINKING_V1 ==="

python3 -m py_compile \
src/scripts/research/build_market_index_context_linking_v1.py

src/scripts/research/build_market_index_context_linking_v1.py \
| tee /tmp/market_index_context_linking_v1.out

grep -q "MARKET_INDEX_CONTEXT_LINKING_V1" \
/tmp/market_index_context_linking_v1.out

grep -q "context_links=" \
/tmp/market_index_context_linking_v1.out

grep -q "db_update=1" \
/tmp/market_index_context_linking_v1.out

grep -q "VERDICT=MARKET_INDEX_CONTEXT_LINKING_OK" \
/tmp/market_index_context_linking_v1.out

echo "TEST_MARKET_INDEX_CONTEXT_LINKING_V1_OK"
