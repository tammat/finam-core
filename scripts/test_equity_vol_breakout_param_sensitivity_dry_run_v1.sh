#!/usr/bin/env bash
set -euo pipefail

cd "$(git rev-parse --show-toplevel)"

echo "=== TEST EQUITY VOL BREAKOUT PARAM SENSITIVITY DRY RUN V1 ==="
echo "runtime_allow=0"
echo "execution_enabled=0"
echo "real_trading_enabled=0"

python3 -m py_compile src/scripts/research/build_equity_vol_breakout_param_sensitivity_dry_run_v1.py

PYTHONPATH=src \
ACTIVE_SINCE_UTC="${ACTIVE_SINCE_UTC:-2026-06-19 07:24:35+00}" \
python3 src/scripts/research/build_equity_vol_breakout_param_sensitivity_dry_run_v1.py \
  | tee /tmp/equity_vol_breakout_param_sensitivity_dry_run_v1.log

grep -q "EQUITY_VOL_BREAKOUT_PARAM_SENSITIVITY_DRY_RUN_V1_OK" /tmp/equity_vol_breakout_param_sensitivity_dry_run_v1.log
grep -q "EQUITY_VOL_BREAKOUT_PARAM_SENSITIVITY_DRY_RUN_SUMMARY" /tmp/equity_vol_breakout_param_sensitivity_dry_run_v1.log
grep -q "EQUITY_VOL_BREAKOUT_SENSITIVITY_GRID_ROW" /tmp/equity_vol_breakout_param_sensitivity_dry_run_v1.log
grep -q "evaluated_rows=" /tmp/equity_vol_breakout_param_sensitivity_dry_run_v1.log
grep -q "best_all_pass=" /tmp/equity_vol_breakout_param_sensitivity_dry_run_v1.log
grep -q "VERDICT=" /tmp/equity_vol_breakout_param_sensitivity_dry_run_v1.log
grep -q "db_update=0" /tmp/equity_vol_breakout_param_sensitivity_dry_run_v1.log

echo
echo "=== EQUITY VOL BREAKOUT PARAM SENSITIVITY SUMMARY ==="
grep -E "EQUITY_VOL_BREAKOUT_SENSITIVITY_SOURCE_ROW|EQUITY_VOL_BREAKOUT_SENSITIVITY_GRID_ROW|evaluated_rows=|best_|VERDICT=" \
  /tmp/equity_vol_breakout_param_sensitivity_dry_run_v1.log | head -260

echo TEST_EQUITY_VOL_BREAKOUT_PARAM_SENSITIVITY_DRY_RUN_V1_OK
