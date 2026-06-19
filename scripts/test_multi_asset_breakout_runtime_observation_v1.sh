#!/usr/bin/env bash
set -euo pipefail

cd "$(git rev-parse --show-toplevel)"

echo "=== TEST MULTI ASSET BREAKOUT RUNTIME OBSERVATION V1 ==="
echo "runtime_allow=0"
echo "execution_enabled=0"
echo "real_trading_enabled=0"
echo "orders_create=0"
echo "execution_intents_create=0"

python3 -m py_compile src/scripts/research/build_multi_asset_breakout_runtime_observation_v1.py

PYTHONPATH=src \
RUNTIME_ALLOW_TRADING=0 EXECUTION_ENABLED=0 REAL_TRADING_ENABLED=0 \
python3 src/scripts/research/build_multi_asset_breakout_runtime_observation_v1.py \
  | tee /tmp/multi_asset_breakout_runtime_observation_v1.log

grep -q "SNAPSHOT_ACCUMULATION" /tmp/multi_asset_breakout_runtime_observation_v1.log
grep -q "READY_DELIVERY_QUALITY" /tmp/multi_asset_breakout_runtime_observation_v1.log
grep -q "FOLLOW_THROUGH_SCHEMA" /tmp/multi_asset_breakout_runtime_observation_v1.log
grep -q "orders_create=0" /tmp/multi_asset_breakout_runtime_observation_v1.log
grep -q "execution_intents_create=0" /tmp/multi_asset_breakout_runtime_observation_v1.log
grep -q "execution_enabled=0" /tmp/multi_asset_breakout_runtime_observation_v1.log
grep -q "real_trading_enabled=0" /tmp/multi_asset_breakout_runtime_observation_v1.log
grep -q "VERDICT=MULTI_ASSET_BREAKOUT_RUNTIME_OBSERVATION_READY" /tmp/multi_asset_breakout_runtime_observation_v1.log
grep -q "MULTI_ASSET_BREAKOUT_RUNTIME_OBSERVATION_V1_OK" /tmp/multi_asset_breakout_runtime_observation_v1.log

echo "=== OBSERVATION SUMMARY ==="
grep -E "SNAPSHOT_ROW|READY_DELIVERY_ROW|status_column=|return_column=|FOLLOW_ROW|edge_readiness=|VERDICT=" \
  /tmp/multi_asset_breakout_runtime_observation_v1.log | head -80

echo TEST_MULTI_ASSET_BREAKOUT_RUNTIME_OBSERVATION_V1_OK
