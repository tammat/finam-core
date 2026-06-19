#!/usr/bin/env bash
set -euo pipefail

cd "$(git rev-parse --show-toplevel)"

echo "=== TEST MULTI ASSET BREAKOUT SIGNAL QUALITY HISTORY V1 ==="
echo "runtime_allow=0"
echo "execution_enabled=0"
echo "real_trading_enabled=0"

python3 -m py_compile src/scripts/research/build_multi_asset_breakout_signal_quality_history_v1.py

PYTHONPATH=src FUTURES_PREFIXES="${FUTURES_PREFIXES:-BR,NG,GD}" \
RUNTIME_ALLOW_TRADING=0 EXECUTION_ENABLED=0 REAL_TRADING_ENABLED=0 \
python3 src/scripts/research/build_multi_asset_breakout_signal_quality_history_v1.py \
  | tee /tmp/multi_asset_breakout_signal_quality_history_v1_dry.log

grep -q "MULTI_ASSET_BREAKOUT_SIGNAL_QUALITY_HISTORY_V1_OK" /tmp/multi_asset_breakout_signal_quality_history_v1_dry.log
grep -q "VERDICT=MULTI_ASSET_BREAKOUT_SIGNAL_QUALITY_HISTORY_DRY_RUN_READY" /tmp/multi_asset_breakout_signal_quality_history_v1_dry.log
grep -q "db_update=0" /tmp/multi_asset_breakout_signal_quality_history_v1_dry.log

PYTHONPATH=src FUTURES_PREFIXES="${FUTURES_PREFIXES:-BR,NG,GD}" \
RUNTIME_ALLOW_TRADING=0 EXECUTION_ENABLED=0 REAL_TRADING_ENABLED=0 \
python3 src/scripts/research/build_multi_asset_breakout_signal_quality_history_v1.py --migrate --save \
  | tee /tmp/multi_asset_breakout_signal_quality_history_v1_save.log

grep -q "MULTI_ASSET_BREAKOUT_SIGNAL_QUALITY_HISTORY_V1_OK" /tmp/multi_asset_breakout_signal_quality_history_v1_save.log
grep -q "VERDICT=MULTI_ASSET_BREAKOUT_SIGNAL_QUALITY_HISTORY_SAVED" /tmp/multi_asset_breakout_signal_quality_history_v1_save.log
grep -q "snapshot_id=" /tmp/multi_asset_breakout_signal_quality_history_v1_save.log
grep -q "snapshot_table_exists=1" /tmp/multi_asset_breakout_signal_quality_history_v1_save.log
grep -q "row_table_exists=1" /tmp/multi_asset_breakout_signal_quality_history_v1_save.log
grep -q "db_update=1" /tmp/multi_asset_breakout_signal_quality_history_v1_save.log
grep -q "execution_changes_required=0" /tmp/multi_asset_breakout_signal_quality_history_v1_save.log

echo "=== MULTI ASSET BREAKOUT SIGNAL QUALITY HISTORY SUMMARY ==="
grep -E "v2_ok=|universe_total=|rows_total=|breakout_ready=|parsed_rows=|parsed_ready_rows=|snapshot_id=|history_snapshots=|history_rows=|history_ready_rows=|VERDICT=" \
  /tmp/multi_asset_breakout_signal_quality_history_v1_save.log

echo TEST_MULTI_ASSET_BREAKOUT_SIGNAL_QUALITY_HISTORY_V1_OK
