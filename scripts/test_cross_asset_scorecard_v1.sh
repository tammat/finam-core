#!/usr/bin/env bash
set -euo pipefail

ROOT="$(git rev-parse --show-toplevel)"
cd "$ROOT"
export PYTHONPATH=src

python3 -m py_compile \
  src/scripts/analytics/build_cross_asset_scorecard_v1.py

python3 src/scripts/analytics/build_cross_asset_scorecard_v1.py \
  | tee /tmp/cross_asset_scorecard_v1.log

grep -q "CROSS ASSET SCORECARD V1" /tmp/cross_asset_scorecard_v1.log
grep -q "ASSET_ROW asset=USD" /tmp/cross_asset_scorecard_v1.log
grep -q "ASSET_ROW asset=GOLD" /tmp/cross_asset_scorecard_v1.log
grep -q "ASSET_ROW asset=BTC" /tmp/cross_asset_scorecard_v1.log
grep -q "CROSS_ASSET_SCORECARD_V1_OK" /tmp/cross_asset_scorecard_v1.log

echo "TEST_CROSS_ASSET_SCORECARD_V1_OK"
