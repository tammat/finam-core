#!/usr/bin/env bash
set -euo pipefail

cd "$(git rev-parse --show-toplevel)"

echo "=== TEST EQUITY STRATEGY WIRING PATCH V1 DRY RUN ==="
echo "runtime_allow=0"
echo "execution_enabled=0"
echo "real_trading_enabled=0"

python3 -m py_compile src/scripts/runtime/build_equity_strategy_wiring_patch_v1_dry_run.py

EQUITY_WIRING_DRY_RUN_SYMBOL="${EQUITY_WIRING_DRY_RUN_SYMBOL:-SBER@MISX}" \
PYTHONPATH=src python3 src/scripts/runtime/build_equity_strategy_wiring_patch_v1_dry_run.py \
  | tee /tmp/equity_strategy_wiring_patch_v1_dry_run.log

grep -q "EQUITY_STRATEGY_WIRING_PATCH_V1_DRY_RUN_OK" /tmp/equity_strategy_wiring_patch_v1_dry_run.log
grep -q "EQUITY_WIRING_DRY_RUN_RUNTIME_ROW" /tmp/equity_strategy_wiring_patch_v1_dry_run.log
grep -q "EQUITY_WIRING_DRY_RUN_FACTORY_SIGNATURE" /tmp/equity_strategy_wiring_patch_v1_dry_run.log
grep -q "EQUITY_WIRING_DRY_RUN_FACTORY_ATTEMPTS" /tmp/equity_strategy_wiring_patch_v1_dry_run.log
grep -q "EQUITY_WIRING_DRY_RUN_FACTORY" /tmp/equity_strategy_wiring_patch_v1_dry_run.log
grep -q "EQUITY_WIRING_DRY_RUN_SUMMARY" /tmp/equity_strategy_wiring_patch_v1_dry_run.log
grep -q "factory_create_ok=1" /tmp/equity_strategy_wiring_patch_v1_dry_run.log
grep -q "resolved_strategy=VOLATILITY_BREAKOUT_EQUITY" /tmp/equity_strategy_wiring_patch_v1_dry_run.log
grep -q "strategy_instance_class=VolatilityBreakoutEquity" /tmp/equity_strategy_wiring_patch_v1_dry_run.log
grep -q "resolved_to_volatility=1" /tmp/equity_strategy_wiring_patch_v1_dry_run.log
grep -q "db_update=0" /tmp/equity_strategy_wiring_patch_v1_dry_run.log
grep -q "file_update=0" /tmp/equity_strategy_wiring_patch_v1_dry_run.log
grep -q "VERDICT=EQUITY_STRATEGY_WIRING_PATCH_DRY_RUN_READY" /tmp/equity_strategy_wiring_patch_v1_dry_run.log

echo
echo "=== EQUITY STRATEGY WIRING PATCH V1 DRY RUN SUMMARY ==="
grep -E "factory_signature=|EQUITY_WIRING_DRY_RUN_FACTORY_ATTEMPT|resolved_strategy=|factory_create_ok=|factory_call_variant=|strategy_instance_class=|expected_volatility=|resolved_to_volatility=|runtime_changes_required=|execution_changes_required=|VERDICT=" \
  /tmp/equity_strategy_wiring_patch_v1_dry_run.log

echo TEST_EQUITY_STRATEGY_WIRING_PATCH_V1_DRY_RUN_OK
