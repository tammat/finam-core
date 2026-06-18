#!/usr/bin/env bash
set -euo pipefail

cd "$(git rev-parse --show-toplevel)"

echo "=== TEST EQUITY STRATEGY WIRING PATCH TARGET AUDIT V1 ==="
echo "runtime_allow=0"
echo "execution_enabled=0"
echo "real_trading_enabled=0"

python3 -m py_compile src/scripts/runtime/build_equity_strategy_wiring_patch_target_audit_v1.py

PYTHONPATH=src python3 src/scripts/runtime/build_equity_strategy_wiring_patch_target_audit_v1.py \
  | tee /tmp/equity_strategy_wiring_patch_target_audit_v1.log

grep -q "EQUITY_STRATEGY_WIRING_PATCH_TARGET_AUDIT_V1_OK" /tmp/equity_strategy_wiring_patch_target_audit_v1.log
grep -q "EQUITY_PATCH_TARGET_FACTORY_CREATE_BLOCKS" /tmp/equity_strategy_wiring_patch_target_audit_v1.log
grep -q "EQUITY_PATCH_TARGET_AUDIT_SUMMARY" /tmp/equity_strategy_wiring_patch_target_audit_v1.log
grep -q "db_update=0" /tmp/equity_strategy_wiring_patch_target_audit_v1.log
grep -q "file_update=0" /tmp/equity_strategy_wiring_patch_target_audit_v1.log
grep -q "VERDICT=" /tmp/equity_strategy_wiring_patch_target_audit_v1.log

echo
echo "=== EQUITY STRATEGY WIRING PATCH TARGET SUMMARY ==="
grep -E "EQUITY_PATCH_TARGET_FACTORY_CREATE_BLOCK|strategy_factory_create_blocks=|equity_candidate_blocks=|patch_target_found=|legacy_mean_reversion_lines=|runtime_universe_lines=|VERDICT=" \
  /tmp/equity_strategy_wiring_patch_target_audit_v1.log

echo TEST_EQUITY_STRATEGY_WIRING_PATCH_TARGET_AUDIT_V1_OK
