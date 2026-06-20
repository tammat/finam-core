#!/usr/bin/env bash
set -euo pipefail

echo "=== INDEX_MARKET_DATA_BACKFILL_AUDIT_V1 ==="

out="$(mktemp)"

python3 -m py_compile src/scripts/research/build_index_market_data_backfill_audit_v1.py
python3 src/scripts/research/build_index_market_data_backfill_audit_v1.py | tee "$out"

grep -q "VERDICT=INDEX_MARKET_DATA_BACKFILL_AUDIT_READY" "$out"
grep -q "TEST_INDEX_MARKET_DATA_BACKFILL_AUDIT_V1_OK" "$out"
grep -q '"db_update": 0' "$out"
grep -q '"runtime_changed": 0' "$out"
grep -q '"execution_changed": 0' "$out"

echo "VERDICT=INDEX_MARKET_DATA_BACKFILL_AUDIT_TEST_OK"
echo "TEST_INDEX_MARKET_DATA_BACKFILL_AUDIT_V1_OK"
