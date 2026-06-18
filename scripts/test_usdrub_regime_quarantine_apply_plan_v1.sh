#!/usr/bin/env bash
set -euo pipefail

cd "$(git rev-parse --show-toplevel)"

echo "=== TEST USDRUB REGIME QUARANTINE APPLY PLAN V1 ==="
echo "runtime_allow=0"
echo "execution_enabled=0"
echo "real_trading_enabled=0"

python3 -m py_compile src/scripts/runtime/build_usdrub_regime_quarantine_apply_plan_v1.py

PYTHONPATH=src python3 src/scripts/runtime/build_usdrub_regime_quarantine_apply_plan_v1.py \
  | tee /tmp/usdrub_regime_quarantine_apply_plan_v1.log

grep -q "USDRUB_REGIME_QUARANTINE_APPLY_PLAN_V1_OK" /tmp/usdrub_regime_quarantine_apply_plan_v1.log
grep -q "USDRUB_QUARANTINE_APPLY_PLAN_SUMMARY" /tmp/usdrub_regime_quarantine_apply_plan_v1.log
grep -q "recommended_action=QUARANTINE_RUNTIME" /tmp/usdrub_regime_quarantine_apply_plan_v1.log
grep -q "recommended_runtime_enabled=0" /tmp/usdrub_regime_quarantine_apply_plan_v1.log
grep -q "recommended_research_only=1" /tmp/usdrub_regime_quarantine_apply_plan_v1.log
grep -q "db_update=0" /tmp/usdrub_regime_quarantine_apply_plan_v1.log
grep -q "VERDICT=" /tmp/usdrub_regime_quarantine_apply_plan_v1.log

echo
echo "=== USDRUB REGIME QUARANTINE APPLY PLAN SUMMARY ==="
grep -E "USDRUB_QUARANTINE_PLAN_ROW|runtime_rows=|runtime_match=|planned_changes=|runtime_changes_required=|recommended_|VERDICT=" \
  /tmp/usdrub_regime_quarantine_apply_plan_v1.log

echo TEST_USDRUB_REGIME_QUARANTINE_APPLY_PLAN_V1_OK
