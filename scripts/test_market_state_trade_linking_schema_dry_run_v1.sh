#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core || exit 1

echo "=== TEST_MARKET_STATE_TRADE_LINKING_SCHEMA_DRY_RUN_V1 ==="

python3 -m py_compile \
  src/scripts/research/build_market_state_trade_linking_schema_dry_run_v1.py

src/scripts/research/build_market_state_trade_linking_schema_dry_run_v1.py \
  | tee /tmp/market_state_trade_linking_schema_dry_run_v1.out

grep -q "MARKET_STATE_TRADE_LINKING_SCHEMA_DRY_RUN_V1" /tmp/market_state_trade_linking_schema_dry_run_v1.out
grep -q "db_update=0" /tmp/market_state_trade_linking_schema_dry_run_v1.out
grep -q "CREATE TABLE IF NOT EXISTS research.trade_state_snapshots_v1" /tmp/market_state_trade_linking_schema_dry_run_v1.out
grep -q "entry_snapshot_id BIGINT REFERENCES research.market_state_snapshots_v1" /tmp/market_state_trade_linking_schema_dry_run_v1.out
grep -q "exit_snapshot_id BIGINT REFERENCES research.market_state_snapshots_v1" /tmp/market_state_trade_linking_schema_dry_run_v1.out
grep -q "CREATE INDEX IF NOT EXISTS idx_trade_state_snapshots_trade_id" /tmp/market_state_trade_linking_schema_dry_run_v1.out
grep -q "guard=no_db_execute" /tmp/market_state_trade_linking_schema_dry_run_v1.out
grep -q "rule=trade_id_unique" /tmp/market_state_trade_linking_schema_dry_run_v1.out
grep -q "VERDICT=MARKET_STATE_TRADE_LINKING_SCHEMA_DRY_RUN_READY" /tmp/market_state_trade_linking_schema_dry_run_v1.out

echo "TEST_MARKET_STATE_TRADE_LINKING_SCHEMA_DRY_RUN_V1_OK"
