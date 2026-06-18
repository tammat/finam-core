#!/usr/bin/env bash
set -euo pipefail

cd "$(git rev-parse --show-toplevel)"

echo "=== TEST EQUITY STRATEGY WIRING PATCH PLAN V1 ==="
echo "runtime_allow=0"
echo "execution_enabled=0"
echo "real_trading_enabled=0"

python3 -m py_compile src/scripts/runtime/build_equity_strategy_wiring_patch_plan_v1.py

PYTHONPATH=src python3 src/scripts/runtime/build_equity_strategy_wiring_patch_plan_v1.py \
  | tee /tmp/equity_strategy_wiring_patch_plan_v1.log

grep -q "EQUITY_STRATEGY_WIRING_PATCH_PLAN_V1_OK" /tmp/equity_strategy_wiring_patch_plan_v1.log
grep -q "EQUITY_STRATEGY_WIRING_PATCH_PLAN_INPUTS" /tmp/equity_strategy_wiring_patch_plan_v1.log
grep -q "EQUITY_STRATEGY_WIRING_PATCH_PLAN_STEPS" /tmp/equity_strategy_wiring_patch_plan_v1.log
grep -q "EQUITY_STRATEGY_WIRING_PATCH_PLAN_GUARDS" /tmp/equity_strategy_wiring_patch_plan_v1.log
grep -q "EQUITY_STRATEGY_WIRING_PATCH_PLAN_SUMMARY" /tmp/equity_strategy_wiring_patch_plan_v1.log
grep -q "needs_patch=1" /tmp/equity_strategy_wiring_patch_plan_v1.log
grep -q "runtime_changes_required=0" /tmp/equity_strategy_wiring_patch_plan_v1.log
grep -q "execution_changes_required=0" /tmp/equity_strategy_wiring_patch_plan_v1.log
grep -q "db_update=0" /tmp/equity_strategy_wiring_patch_plan_v1.log
grep -q "file_update=0" /tmp/equity_strategy_wiring_patch_plan_v1.log
grep -q "VERDICT=EQUITY_STRATEGY_WIRING_PATCH_PLAN_READY" /tmp/equity_strategy_wiring_patch_plan_v1.log

echo
echo "=== EQUITY STRATEGY WIRING PATCH PLAN SUMMARY ==="
grep -E "factory_supports_volatility=|volatility_class_exists=|paper_uses_strategy_factory=|paper_uses_volatility=|paper_uses_legacy_mean_reversion=|needs_patch=|decision=|VERDICT=" \
  /tmp/equity_strategy_wiring_patch_plan_v1.log

echo TEST_EQUITY_STRATEGY_WIRING_PATCH_PLAN_V1_OK
