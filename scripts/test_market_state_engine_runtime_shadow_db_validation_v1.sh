#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core || exit 1

echo "=== TEST_MARKET_STATE_ENGINE_RUNTIME_SHADOW_DB_VALIDATION_V1 ==="

python3 -m py_compile \
  src/scripts/research/build_market_state_engine_runtime_shadow_db_validation_v1.py

src/scripts/research/build_market_state_engine_runtime_shadow_db_validation_v1.py \
  | tee /tmp/market_state_engine_runtime_shadow_db_validation_v1.out

grep -q "MARKET_STATE_ENGINE_RUNTIME_SHADOW_DB_VALIDATION_V1" /tmp/market_state_engine_runtime_shadow_db_validation_v1.out
grep -q "runtime_changed=0" /tmp/market_state_engine_runtime_shadow_db_validation_v1.out
grep -q "execution_changed=0" /tmp/market_state_engine_runtime_shadow_db_validation_v1.out
grep -q "real_trading_enabled=0" /tmp/market_state_engine_runtime_shadow_db_validation_v1.out
grep -q "orders_sent=0" /tmp/market_state_engine_runtime_shadow_db_validation_v1.out
grep -q "shadow_snapshots=" /tmp/market_state_engine_runtime_shadow_db_validation_v1.out
grep -q "missing_values=0" /tmp/market_state_engine_runtime_shadow_db_validation_v1.out
grep -q "missing_metadata=0" /tmp/market_state_engine_runtime_shadow_db_validation_v1.out
grep -q "VERDICT=MARKET_STATE_ENGINE_RUNTIME_SHADOW_DB_VALIDATION_OK" /tmp/market_state_engine_runtime_shadow_db_validation_v1.out

echo "TEST_MARKET_STATE_ENGINE_RUNTIME_SHADOW_DB_VALIDATION_V1_OK"
