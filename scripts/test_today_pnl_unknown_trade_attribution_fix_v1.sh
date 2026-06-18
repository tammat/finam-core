#!/usr/bin/env bash
set -euo pipefail

cd "$(git rev-parse --show-toplevel)"

echo "=== TEST TODAY PNL UNKNOWN TRADE ATTRIBUTION FIX V1 ==="
echo "runtime_allow=0"
echo "execution_enabled=0"
echo "real_trading_enabled=0"

python3 -m py_compile src/scripts/runtime/build_today_pnl_unknown_trade_attribution_fix_v1.py

PYTHONPATH=src python3 src/scripts/runtime/build_today_pnl_unknown_trade_attribution_fix_v1.py \
  | tee /tmp/today_pnl_unknown_trade_attribution_fix_v1.log

grep -q "TODAY_PNL_UNKNOWN_TRADE_ATTRIBUTION_FIX_V1_OK" /tmp/today_pnl_unknown_trade_attribution_fix_v1.log
grep -q "TODAY_PNL_UNKNOWN_ATTRIBUTION_SUMMARY" /tmp/today_pnl_unknown_trade_attribution_fix_v1.log
grep -q "db_update=0" /tmp/today_pnl_unknown_trade_attribution_fix_v1.log
grep -q "execution_changes_required=0" /tmp/today_pnl_unknown_trade_attribution_fix_v1.log
grep -q "VERDICT=" /tmp/today_pnl_unknown_trade_attribution_fix_v1.log

echo
echo "=== TODAY PNL UNKNOWN ATTRIBUTION SUMMARY ==="
grep -E "TODAY_PNL_UNKNOWN_ATTRIBUTION_ROW|unknown_rows=|apply_candidates=|high_confidence=|medium_confidence=|VERDICT=" \
  /tmp/today_pnl_unknown_trade_attribution_fix_v1.log

echo TEST_TODAY_PNL_UNKNOWN_TRADE_ATTRIBUTION_FIX_V1_OK
