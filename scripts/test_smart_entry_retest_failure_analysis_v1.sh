#!/usr/bin/env bash
set -euo pipefail

cd "$(git rev-parse --show-toplevel)"

echo "=== TEST SMART ENTRY RETEST FAILURE ANALYSIS V1 ==="
echo "runtime_allow=0"
echo "execution_enabled=0"
echo "real_trading_enabled=0"

python3 -m py_compile \
  src/scripts/research/build_smart_entry_retest_failure_analysis_v1.py

SMART_ENTRY_RETEST_LOOKBACK="${SMART_ENTRY_RETEST_LOOKBACK:-30 days}" \
SMART_ENTRY_RETEST_LIMIT="${SMART_ENTRY_RETEST_LIMIT:-50000}" \
PYTHONPATH=src python3 src/scripts/research/build_smart_entry_retest_failure_analysis_v1.py \
  | tee /tmp/smart_entry_retest_failure_analysis_v1.log

grep -q "SMART_ENTRY_RETEST_FAILURE_ANALYSIS_V1_OK" /tmp/smart_entry_retest_failure_analysis_v1.log
grep -q "SMART_ENTRY_RETEST_BY_STRATEGY" /tmp/smart_entry_retest_failure_analysis_v1.log
grep -q "SMART_ENTRY_RETEST_BY_EXIT_CLASS" /tmp/smart_entry_retest_failure_analysis_v1.log
grep -q "SMART_ENTRY_RETEST_FAILURE_ANALYSIS_SUMMARY" /tmp/smart_entry_retest_failure_analysis_v1.log
grep -q "VERDICT=" /tmp/smart_entry_retest_failure_analysis_v1.log

echo
echo "=== SMART ENTRY RETEST FAILURE SUMMARY ==="
grep -E "SMART_ENTRY_RETEST_STRATEGY_ROW|SMART_ENTRY_RETEST_EXIT_ROW|SMART_ENTRY_RETEST_SESSION_ROW|SMART_ENTRY_RETEST_REGIME_ROW|pairs_total=|wins=|losses=|winrate=|total_net_pnl=|net_pnl_per_pair=|VERDICT=" \
  /tmp/smart_entry_retest_failure_analysis_v1.log \
  | head -220

echo TEST_SMART_ENTRY_RETEST_FAILURE_ANALYSIS_V1_OK
