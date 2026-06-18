#!/usr/bin/env bash
set -euo pipefail

cd "$(git rev-parse --show-toplevel)"

echo "=== TEST USDRUB REGIME FEE DRAG GUARD PLAN V1 ==="
echo "runtime_allow=0"
echo "execution_enabled=0"
echo "real_trading_enabled=0"

python3 -m py_compile src/scripts/runtime/build_usdrub_regime_fee_drag_guard_plan_v1.py

PYTHONPATH=src python3 src/scripts/runtime/build_usdrub_regime_fee_drag_guard_plan_v1.py \
  | tee /tmp/usdrub_regime_fee_drag_guard_plan_v1.log

grep -q "USDRUB_REGIME_FEE_DRAG_GUARD_PLAN_V1_OK" /tmp/usdrub_regime_fee_drag_guard_plan_v1.log
grep -q "USDRUB_FEE_DRAG_METRICS" /tmp/usdrub_regime_fee_drag_guard_plan_v1.log
grep -q "USDRUB_FEE_DRAG_GUARD_RECOMMENDATION" /tmp/usdrub_regime_fee_drag_guard_plan_v1.log
grep -q "recommended_action=QUARANTINE_RUNTIME" /tmp/usdrub_regime_fee_drag_guard_plan_v1.log
grep -q "recommended_research_only=1" /tmp/usdrub_regime_fee_drag_guard_plan_v1.log
grep -q "VERDICT=" /tmp/usdrub_regime_fee_drag_guard_plan_v1.log
grep -q "db_update=0" /tmp/usdrub_regime_fee_drag_guard_plan_v1.log

echo
echo "=== USDRUB REGIME FEE DRAG GUARD PLAN SUMMARY ==="
grep -E "trades=|closed_cycles=|gross_pnl=|commission=|net_pnl=|avg_gross_per_cycle=|avg_commission_per_cycle=|recommended_|VERDICT=" \
  /tmp/usdrub_regime_fee_drag_guard_plan_v1.log

echo TEST_USDRUB_REGIME_FEE_DRAG_GUARD_PLAN_V1_OK
