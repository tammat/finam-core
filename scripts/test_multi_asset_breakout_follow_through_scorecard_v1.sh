#!/usr/bin/env bash
set -euo pipefail

cd "$(git rev-parse --show-toplevel)"

echo "=== TEST MULTI ASSET BREAKOUT FOLLOW THROUGH SCORECARD V1 ==="
echo "runtime_allow=0"
echo "execution_enabled=0"
echo "real_trading_enabled=0"
echo "real_execution=0"

python3 -m py_compile src/scripts/research/build_multi_asset_breakout_follow_through_scorecard_v1.py

PYTHONPATH=src \
RUNTIME_ALLOW_TRADING=0 EXECUTION_ENABLED=0 REAL_TRADING_ENABLED=0 \
python3 src/scripts/research/build_multi_asset_breakout_follow_through_scorecard_v1.py \
  | tee /tmp/multi_asset_breakout_follow_through_scorecard_v1.log

grep -q "MULTI_ASSET_BREAKOUT_FOLLOW_THROUGH_SCORECARD_V1_OK" /tmp/multi_asset_breakout_follow_through_scorecard_v1.log
grep -q "MULTI_ASSET_BREAKOUT_FOLLOW_THROUGH_SCORECARD_SUMMARY" /tmp/multi_asset_breakout_follow_through_scorecard_v1.log
grep -q "ready_rows=" /tmp/multi_asset_breakout_follow_through_scorecard_v1.log
grep -q "scorecard_rows_total=" /tmp/multi_asset_breakout_follow_through_scorecard_v1.log
grep -q "db_update=1" /tmp/multi_asset_breakout_follow_through_scorecard_v1.log
grep -q "runtime_changes_required=0" /tmp/multi_asset_breakout_follow_through_scorecard_v1.log
grep -q "execution_changes_required=0" /tmp/multi_asset_breakout_follow_through_scorecard_v1.log
grep -q "real_trading_enabled=0" /tmp/multi_asset_breakout_follow_through_scorecard_v1.log
grep -q "execution_enabled=0" /tmp/multi_asset_breakout_follow_through_scorecard_v1.log
grep -q "VERDICT=" /tmp/multi_asset_breakout_follow_through_scorecard_v1.log

echo "=== MULTI ASSET BREAKOUT FOLLOW THROUGH SCORECARD SUMMARY ==="
grep -E "ready_rows=|generated_rows=|waiting_rows=|scorecard_rows_total=|horizon_min=|VERDICT=" \
  /tmp/multi_asset_breakout_follow_through_scorecard_v1.log

echo TEST_MULTI_ASSET_BREAKOUT_FOLLOW_THROUGH_SCORECARD_V1_OK
