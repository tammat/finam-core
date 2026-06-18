#!/usr/bin/env bash
set -euo pipefail

cd "$(git rev-parse --show-toplevel)"

echo "=== TEST SMART ENTRY RETEST QUARANTINE PLAN V1 ==="
echo "runtime_allow=0"
echo "execution_enabled=0"
echo "real_trading_enabled=0"

python3 -m py_compile \
  src/scripts/research/build_smart_entry_retest_failure_analysis_v1.py \
  src/scripts/research/build_smart_entry_retest_quarantine_plan_v1.py

PYTHONPATH=src python3 src/scripts/research/build_smart_entry_retest_quarantine_plan_v1.py \
  | tee /tmp/smart_entry_retest_quarantine_plan_v1.log

grep -q "SMART_ENTRY_RETEST_QUARANTINE_PLAN_V1_OK" /tmp/smart_entry_retest_quarantine_plan_v1.log
grep -q "SMART_ENTRY_RETEST_QUARANTINE_PLAN_ROWS" /tmp/smart_entry_retest_quarantine_plan_v1.log
grep -q "SMART_ENTRY_RETEST_QUARANTINE_PLAN_SUMMARY" /tmp/smart_entry_retest_quarantine_plan_v1.log
grep -q "VERDICT=" /tmp/smart_entry_retest_quarantine_plan_v1.log

echo
echo "=== SMART ENTRY RETEST QUARANTINE PLAN SUMMARY ==="
grep -E "SMART_ENTRY_RETEST_QUARANTINE_PLAN_ROW|rows_total=|quarantine_runtime_candidates=|research_only=|research_only_with_session_filter=|require_more_data=|VERDICT=" \
  /tmp/smart_entry_retest_quarantine_plan_v1.log

echo TEST_SMART_ENTRY_RETEST_QUARANTINE_PLAN_V1_OK
