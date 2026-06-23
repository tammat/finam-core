#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_MULTI_ASSET_COMPRESSION_FOLLOW_THROUGH_SCORECARD_V1_1 ==="

python3 src/scripts/research/build_multi_asset_compression_follow_through_scorecard_v1_1.py \
  | tee /tmp/multi_asset_compression_follow_through_scorecard_v1_1.log

grep -q "NO_LOOKAHEAD" /tmp/multi_asset_compression_follow_through_scorecard_v1_1.log
grep -q "MULTI_ASSET_COMPRESSION_FOLLOW_THROUGH_SCORECARD_V1_1_SUMMARY" /tmp/multi_asset_compression_follow_through_scorecard_v1_1.log
grep -Eq "VERDICT=MULTI_ASSET_COMPRESSION_FOLLOW_THROUGH_(HAS_CANDIDATES|NO_POSITIVE_EDGE)" /tmp/multi_asset_compression_follow_through_scorecard_v1_1.log

echo "TEST_MULTI_ASSET_COMPRESSION_FOLLOW_THROUGH_SCORECARD_V1_1_OK"
