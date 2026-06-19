#!/usr/bin/env bash
set -euo pipefail

cd "$(git rev-parse --show-toplevel)"

echo "=== TEST MULTI ASSET WATCH LAYER HEALTHCHECK V1 ==="
echo "runtime_allow=0"
echo "execution_enabled=0"
echo "real_trading_enabled=0"

python3 -m py_compile src/scripts/research/build_multi_asset_watch_layer_healthcheck_v1.py

PYTHONPATH=src FUTURES_PREFIXES="${FUTURES_PREFIXES:-BR,NG,GD}" \
python3 src/scripts/research/build_multi_asset_watch_layer_healthcheck_v1.py \
  | tee /tmp/multi_asset_watch_layer_healthcheck_v1.log

grep -q "MULTI_ASSET_WATCH_LAYER_HEALTHCHECK_V1_OK" /tmp/multi_asset_watch_layer_healthcheck_v1.log
grep -q "MULTI_ASSET_WATCH_LAYER_HEALTHCHECK_SUMMARY" /tmp/multi_asset_watch_layer_healthcheck_v1.log
grep -q "source_ok=" /tmp/multi_asset_watch_layer_healthcheck_v1.log
grep -q "expiry_plan_ok=" /tmp/multi_asset_watch_layer_healthcheck_v1.log
grep -q "selection_ok=" /tmp/multi_asset_watch_layer_healthcheck_v1.log
grep -q "v2_ok=" /tmp/multi_asset_watch_layer_healthcheck_v1.log
grep -q "breakout_ready=" /tmp/multi_asset_watch_layer_healthcheck_v1.log
grep -q "VERDICT=" /tmp/multi_asset_watch_layer_healthcheck_v1.log
grep -q "db_update=0" /tmp/multi_asset_watch_layer_healthcheck_v1.log

echo "=== MULTI ASSET WATCH LAYER HEALTHCHECK SUMMARY ==="
grep -E "SOURCE_HAS_|journal_|expiry_|selection_|v2_|source_ok=|runtime_equity_rows=|breakout_ready=|py_compile_failures=|VERDICT=" \
  /tmp/multi_asset_watch_layer_healthcheck_v1.log

echo TEST_MULTI_ASSET_WATCH_LAYER_HEALTHCHECK_V1_OK
