#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_EQUITY_VOL_BREAKOUT_PARAMETER_RESEARCH_V1 ==="

python3 src/scripts/research/build_equity_vol_breakout_parameter_research_v1.py \
  | tee /tmp/equity_vol_breakout_parameter_research_v1.log

grep -q "EQUITY_VOL_BREAKOUT_PARAMETER_RESEARCH_V1" /tmp/equity_vol_breakout_parameter_research_v1.log
grep -q "db_update=0" /tmp/equity_vol_breakout_parameter_research_v1.log
grep -q "real_trading_enabled=0" /tmp/equity_vol_breakout_parameter_research_v1.log
grep -q "VERDICT=" /tmp/equity_vol_breakout_parameter_research_v1.log

echo "TEST_EQUITY_VOL_BREAKOUT_PARAMETER_RESEARCH_V1_OK"
