#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core || exit 1

echo "=== TEST_MARKET_STATE_ENGINE_DATABASE_SCHEMA_APPLY_V1 ==="

python3 -m py_compile \
  src/scripts/research/apply_market_state_engine_database_schema_v1.py

src/scripts/research/apply_market_state_engine_database_schema_v1.py --apply \
  | tee /tmp/market_state_engine_database_schema_apply_v1.out

grep -q "MARKET_STATE_ENGINE_DATABASE_SCHEMA_APPLY_V1" /tmp/market_state_engine_database_schema_apply_v1.out
grep -q "db_update=1" /tmp/market_state_engine_database_schema_apply_v1.out
grep -q "tables_applied=4" /tmp/market_state_engine_database_schema_apply_v1.out
grep -q "indexes_applied=3" /tmp/market_state_engine_database_schema_apply_v1.out
grep -q "runtime_changed=0" /tmp/market_state_engine_database_schema_apply_v1.out
grep -q "execution_changed=0" /tmp/market_state_engine_database_schema_apply_v1.out
grep -q "real_trading_enabled=0" /tmp/market_state_engine_database_schema_apply_v1.out
grep -q "VERDICT=MARKET_STATE_ENGINE_DATABASE_SCHEMA_APPLY_OK" /tmp/market_state_engine_database_schema_apply_v1.out

echo "TEST_MARKET_STATE_ENGINE_DATABASE_SCHEMA_APPLY_V1_OK"
