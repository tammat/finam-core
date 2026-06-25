#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core || exit 1

echo "=== TEST_MARKET_INDEX_STATE_SCHEMA_DRY_RUN_V1 ==="

python3 -m py_compile \
  src/scripts/research/build_market_index_state_schema_dry_run_v1.py

src/scripts/research/build_market_index_state_schema_dry_run_v1.py \
  | tee /tmp/market_index_state_schema_dry_run_v1.out

grep -q "MARKET_INDEX_STATE_SCHEMA_DRY_RUN_V1" /tmp/market_index_state_schema_dry_run_v1.out
grep -q "CREATE TABLE IF NOT EXISTS research.market_index_state_context_v1" /tmp/market_index_state_schema_dry_run_v1.out
grep -q "CREATE TABLE IF NOT EXISTS research.market_state_index_context_links_v1" /tmp/market_index_state_schema_dry_run_v1.out
grep -q "guard=no_db_execute" /tmp/market_index_state_schema_dry_run_v1.out
grep -q "rule=context_signature_is_separate_from_instrument_signature" /tmp/market_index_state_schema_dry_run_v1.out
grep -q "VERDICT=MARKET_INDEX_STATE_SCHEMA_DRY_RUN_READY" /tmp/market_index_state_schema_dry_run_v1.out

echo "TEST_MARKET_INDEX_STATE_SCHEMA_DRY_RUN_V1_OK"
