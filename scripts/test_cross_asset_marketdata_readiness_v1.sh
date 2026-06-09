#!/usr/bin/env bash
set -euo pipefail

ROOT="$(git rev-parse --show-toplevel)"
cd "$ROOT"
export PYTHONPATH=src

python3 -m py_compile \
  src/scripts/analytics/build_cross_asset_marketdata_readiness_v1.py

python3 src/scripts/analytics/build_cross_asset_marketdata_readiness_v1.py \
  | tee /tmp/cross_asset_marketdata_readiness_v1.log

grep -q "CROSS ASSET MARKETDATA READINESS V1" /tmp/cross_asset_marketdata_readiness_v1.log
grep -q "READINESS_ROW asset=USD" /tmp/cross_asset_marketdata_readiness_v1.log
grep -q "READINESS_ROW asset=GOLD" /tmp/cross_asset_marketdata_readiness_v1.log
grep -q "READINESS_ROW asset=BTC" /tmp/cross_asset_marketdata_readiness_v1.log
grep -q "READINESS_ROW asset=ETH" /tmp/cross_asset_marketdata_readiness_v1.log
grep -q "CROSS_ASSET_MARKETDATA_READINESS_V1_OK" /tmp/cross_asset_marketdata_readiness_v1.log

echo "TEST_CROSS_ASSET_MARKETDATA_READINESS_V1_OK"
