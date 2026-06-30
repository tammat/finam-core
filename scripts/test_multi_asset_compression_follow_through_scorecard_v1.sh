#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_MULTI_ASSET_COMPRESSION_FOLLOW_THROUGH_SCORECARD_V1 ==="

python3 src/scripts/research/build_multi_asset_compression_follow_through_scorecard_v1.py \
  | tee /tmp/multi_asset_compression_follow_through_scorecard_v1.log

grep -q "db_update=0" /tmp/multi_asset_compression_follow_through_scorecard_v1.log
grep -q "runtime_changed=0" /tmp/multi_asset_compression_follow_through_scorecard_v1.log
grep -q "execution_changed=0" /tmp/multi_asset_compression_follow_through_scorecard_v1.log
grep -q "real_trading_enabled=0" /tmp/multi_asset_compression_follow_through_scorecard_v1.log
grep -q "VERDICT=" /tmp/multi_asset_compression_follow_through_scorecard_v1.log

echo "TEST_MULTI_ASSET_COMPRESSION_FOLLOW_THROUGH_SCORECARD_V1_OK"
