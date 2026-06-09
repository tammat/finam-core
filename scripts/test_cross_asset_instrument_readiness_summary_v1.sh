#!/usr/bin/env bash
set -euo pipefail

ROOT="$(git rev-parse --show-toplevel)"
cd "$ROOT"
export PYTHONPATH=src

python3 -m py_compile \
  src/scripts/analytics/build_cross_asset_instrument_readiness_summary_v1.py

python3 src/scripts/analytics/build_cross_asset_instrument_readiness_summary_v1.py \
  | tee /tmp/cross_asset_instrument_readiness_summary_v1.log

grep -q "CROSS ASSET INSTRUMENT READINESS SUMMARY V1" /tmp/cross_asset_instrument_readiness_summary_v1.log
grep -q "SUMMARY_ROWS" /tmp/cross_asset_instrument_readiness_summary_v1.log
grep -q "SUMMARY_ROW priority=1" /tmp/cross_asset_instrument_readiness_summary_v1.log
grep -q "CROSS_ASSET_INSTRUMENT_READINESS_SUMMARY_V1_OK" /tmp/cross_asset_instrument_readiness_summary_v1.log

echo "TEST_CROSS_ASSET_INSTRUMENT_READINESS_SUMMARY_V1_OK"
