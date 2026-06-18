#!/usr/bin/env bash
set -euo pipefail

cd "$(git rev-parse --show-toplevel)"

echo "=== TEST SMART ENTRY RETEST QUARANTINE APPLY DRY RUN V1 ==="
echo "runtime_allow=0"
echo "execution_enabled=0"
echo "real_trading_enabled=0"

python3 -m py_compile \
  src/scripts/research/build_smart_entry_retest_quarantine_plan_v1.py \
  src/scripts/research/build_smart_entry_retest_quarantine_apply_dry_run_v1.py

PYTHONPATH=src python3 src/scripts/research/build_smart_entry_retest_quarantine_apply_dry_run_v1.py \
  | tee /tmp/smart_entry_retest_quarantine_apply_dry_run_v1.log

grep -q "SMART_ENTRY_RETEST_QUARANTINE_APPLY_DRY_RUN_V1_OK" /tmp/smart_entry_retest_quarantine_apply_dry_run_v1.log
grep -q "SMART_ENTRY_RETEST_QUARANTINE_DRY_RUN_ROWS" /tmp/smart_entry_retest_quarantine_apply_dry_run_v1.log
grep -q "SMART_ENTRY_RETEST_QUARANTINE_APPLY_DRY_RUN_SUMMARY" /tmp/smart_entry_retest_quarantine_apply_dry_run_v1.log
grep -q "db_update=0" /tmp/smart_entry_retest_quarantine_apply_dry_run_v1.log
grep -q "VERDICT=" /tmp/smart_entry_retest_quarantine_apply_dry_run_v1.log

echo
echo "=== SMART ENTRY RETEST QUARANTINE APPLY DRY RUN SUMMARY ==="
grep -E "SMART_ENTRY_RETEST_QUARANTINE_DRY_RUN_ROW|plan_rows=|runtime_rows=|quarantine_runtime_candidates=|planned_changes=|no_runtime_match=|db_update=0|VERDICT=" \
  /tmp/smart_entry_retest_quarantine_apply_dry_run_v1.log

echo TEST_SMART_ENTRY_RETEST_QUARANTINE_APPLY_DRY_RUN_V1_OK
