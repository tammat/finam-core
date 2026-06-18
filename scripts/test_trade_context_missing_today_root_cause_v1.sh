#!/usr/bin/env bash
set -euo pipefail

cd "$(git rev-parse --show-toplevel)"

echo "=== TEST TRADE CONTEXT MISSING TODAY ROOT CAUSE V1 ==="
echo "runtime_allow=0"
echo "execution_enabled=0"
echo "real_trading_enabled=0"

python3 -m py_compile \
  src/scripts/research/build_trade_context_missing_today_root_cause_v1.py

PYTHONPATH=src python3 src/scripts/research/build_trade_context_missing_today_root_cause_v1.py \
  | tee /tmp/trade_context_missing_today_root_cause_v1.log

grep -q "TRADE_CONTEXT_MISSING_TODAY_ROOT_CAUSE_V1_OK" /tmp/trade_context_missing_today_root_cause_v1.log
grep -q "VERDICT=" /tmp/trade_context_missing_today_root_cause_v1.log

echo
echo "=== ROOT CAUSE SUMMARY ==="
grep -E "MISSING_CONTEXT_SUMMARY_ROW|MISSING_CONTEXT_ROW|bad_rows=|VERDICT=" \
  /tmp/trade_context_missing_today_root_cause_v1.log

echo TEST_TRADE_CONTEXT_MISSING_TODAY_ROOT_CAUSE_V1_OK
