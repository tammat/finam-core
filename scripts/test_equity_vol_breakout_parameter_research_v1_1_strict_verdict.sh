#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_EQUITY_VOL_BREAKOUT_PARAMETER_RESEARCH_V1_1_STRICT_VERDICT ==="

python3 src/scripts/research/build_equity_vol_breakout_parameter_research_v1_1_strict_verdict.py \
  | tee /tmp/equity_vol_breakout_parameter_research_v1_1_strict_verdict.log

grep -q "STRICT_SUMMARY" /tmp/equity_vol_breakout_parameter_research_v1_1_strict_verdict.log
grep -q "VERDICT=EQUITY_VOL_BREAKOUT_NO_POSITIVE_EDGE" /tmp/equity_vol_breakout_parameter_research_v1_1_strict_verdict.log
grep -q "real_trading_enabled=0" /tmp/equity_vol_breakout_parameter_research_v1_1_strict_verdict.log
grep -q "execution_changed=0" /tmp/equity_vol_breakout_parameter_research_v1_1_strict_verdict.log

echo "TEST_EQUITY_VOL_BREAKOUT_PARAMETER_RESEARCH_V1_1_STRICT_VERDICT_OK"
