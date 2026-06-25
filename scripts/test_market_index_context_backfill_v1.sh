#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core || exit 1

echo "=== TEST_MARKET_INDEX_CONTEXT_BACKFILL_V1 ==="

python3 -m py_compile \
src/scripts/research/build_market_index_context_backfill_v1.py

PYTHONPATH=src \
src/scripts/research/build_market_index_context_backfill_v1.py \
| tee /tmp/market_index_context_backfill_v1.out

grep -q "MARKET_INDEX_CONTEXT_BACKFILL_V1" \
/tmp/market_index_context_backfill_v1.out

grep -q "contexts_written=" \
/tmp/market_index_context_backfill_v1.out

grep -q "db_update=1" \
/tmp/market_index_context_backfill_v1.out

grep -q "VERDICT=MARKET_INDEX_CONTEXT_BACKFILL_OK" \
/tmp/market_index_context_backfill_v1.out

echo "TEST_MARKET_INDEX_CONTEXT_BACKFILL_V1_OK"
