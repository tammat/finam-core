#!/usr/bin/env bash
set -euo pipefail

cd "$(git rev-parse --show-toplevel)"

echo "=== TEST SMART ENTRY RETEST QUARANTINE APPLY PLAN REVIEW V1 ==="
echo "runtime_allow=0"
echo "execution_enabled=0"
echo "real_trading_enabled=0"

python3 -m py_compile \
  src/scripts/research/build_smart_entry_retest_quarantine_apply_dry_run_v1.py \
  src/scripts/research/build_smart_entry_retest_quarantine_apply_plan_review_v1.py

PYTHONPATH=src python3 src/scripts/research/build_smart_entry_retest_quarantine_apply_plan_review_v1.py \
  | tee /tmp/smart_entry_retest_quarantine_apply_plan_review_v1.log

grep -q "SMART_ENTRY_RETEST_QUARANTINE_APPLY_PLAN_REVIEW_V1_OK" /tmp/smart_entry_retest_quarantine_apply_plan_review_v1.log
grep -q "SMART_ENTRY_RETEST_QUARANTINE_APPLY_PLAN_REVIEW_ROWS" /tmp/smart_entry_retest_quarantine_apply_plan_review_v1.log
grep -q "SMART_ENTRY_RETEST_QUARANTINE_APPLY_PLAN_REVIEW_SUMMARY" /tmp/smart_entry_retest_quarantine_apply_plan_review_v1.log
grep -q "db_update=0" /tmp/smart_entry_retest_quarantine_apply_plan_review_v1.log
grep -q "VERDICT=" /tmp/smart_entry_retest_quarantine_apply_plan_review_v1.log

if grep -q "APPLY_CANDIDATE_REQUIRES_MANUAL_APPROVAL" /tmp/smart_entry_retest_quarantine_apply_plan_review_v1.log; then
  echo "FAIL: review still has apply candidates"
  exit 1
fi

echo
echo "=== APPLY PLAN REVIEW SUMMARY ==="
grep -E "SMART_ENTRY_RETEST_QUARANTINE_APPLY_PLAN_REVIEW_ROW|apply_candidates=|already_disabled=|no_runtime_match=|research_only=|require_more_data=|db_update=0|VERDICT=" \
  /tmp/smart_entry_retest_quarantine_apply_plan_review_v1.log

echo TEST_SMART_ENTRY_RETEST_QUARANTINE_APPLY_PLAN_REVIEW_V1_OK
