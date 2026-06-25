#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core || exit 1

echo "=== TEST_MARKET_STATE_ENGINE_DATABASE_SCHEMA_DRY_RUN_V1 ==="

python3 -m py_compile \
  src/scripts/research/build_market_state_engine_database_schema_dry_run_v1.py

src/scripts/research/build_market_state_engine_database_schema_dry_run_v1.py \
  | tee /tmp/market_state_engine_database_schema_dry_run_v1.out

grep -q "MARKET_STATE_ENGINE_DATABASE_SCHEMA_DRY_RUN_V1" /tmp/market_state_engine_database_schema_dry_run_v1.out
grep -q "db_update=0" /tmp/market_state_engine_database_schema_dry_run_v1.out
grep -q "CREATE SCHEMA IF NOT EXISTS research" /tmp/market_state_engine_database_schema_dry_run_v1.out
grep -q "CREATE TABLE IF NOT EXISTS research.market_state_snapshots_v1" /tmp/market_state_engine_database_schema_dry_run_v1.out
grep -q "CREATE TABLE IF NOT EXISTS research.market_state_snapshot_values_v1" /tmp/market_state_engine_database_schema_dry_run_v1.out
grep -q "CREATE TABLE IF NOT EXISTS research.market_state_snapshot_metadata_v1" /tmp/market_state_engine_database_schema_dry_run_v1.out
grep -q "CREATE TABLE IF NOT EXISTS research.market_state_transitions_v1" /tmp/market_state_engine_database_schema_dry_run_v1.out
grep -q "guard=no_db_execute" /tmp/market_state_engine_database_schema_dry_run_v1.out
grep -q "rule=idempotent_schema" /tmp/market_state_engine_database_schema_dry_run_v1.out
grep -q "VERDICT=MARKET_STATE_ENGINE_DATABASE_SCHEMA_DRY_RUN_READY" /tmp/market_state_engine_database_schema_dry_run_v1.out

echo "TEST_MARKET_STATE_ENGINE_DATABASE_SCHEMA_DRY_RUN_V1_OK"
