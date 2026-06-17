#!/usr/bin/env bash
set -euo pipefail

cd "$(git rev-parse --show-toplevel)"

echo "=== TEST FUTURES REAL BLOCK GUARD PROTECTIVE WIRING AUDIT V2 ==="
echo "runtime_allow=0"
echo "execution_enabled=0"

python3 -m py_compile \
  src/scripts/research/build_futures_real_block_guard_protective_wiring_audit_v2.py \
  src/finam_core/risk/futures_real_block_guard_v1.py \
  src/finam_core/execution/finam_order_client_adapter.py \
  src/finam_core/execution/execution_dispatcher.py \
  src/finam_core/execution/oco_order_manager.py \
  src/scripts/run_synthetic_protective_real_sell_adapter.py

python3 src/scripts/research/build_futures_real_block_guard_protective_wiring_audit_v2.py \
  | tee /tmp/futures_real_block_guard_protective_wiring_audit_v2.log

grep -q "FUTURES_REAL_BLOCK_GUARD_PROTECTIVE_WIRING_AUDIT_V2_OK" /tmp/futures_real_block_guard_protective_wiring_audit_v2.log
grep -q "VERDICT=FUTURES_REAL_BLOCK_GUARD_PROTECTIVE_WIRING_COMPLETE" /tmp/futures_real_block_guard_protective_wiring_audit_v2.log
grep -q "guard_required_rows=0" /tmp/futures_real_block_guard_protective_wiring_audit_v2.log
grep -q "GUARD_REQUIRED=none" /tmp/futures_real_block_guard_protective_wiring_audit_v2.log
grep -q "BROKER_ADAPTER_GUARDED" /tmp/futures_real_block_guard_protective_wiring_audit_v2.log
grep -q "DISPATCHER_GUARDED" /tmp/futures_real_block_guard_protective_wiring_audit_v2.log
grep -q "OCO_GUARDED" /tmp/futures_real_block_guard_protective_wiring_audit_v2.log
grep -q "SYNTHETIC_PROTECTIVE_GUARDED" /tmp/futures_real_block_guard_protective_wiring_audit_v2.log
grep -q "runtime_allow=0" /tmp/futures_real_block_guard_protective_wiring_audit_v2.log
grep -q "execution_enabled=0" /tmp/futures_real_block_guard_protective_wiring_audit_v2.log

echo
echo "=== GUARDED PATHS ==="
grep "PROTECTIVE_WIRING_V2_ROW" /tmp/futures_real_block_guard_protective_wiring_audit_v2.log \
  | grep "GUARDED"

echo
echo "=== REVIEW PATHS ==="
grep "REVIEW=" /tmp/futures_real_block_guard_protective_wiring_audit_v2.log || true

echo TEST_FUTURES_REAL_BLOCK_GUARD_PROTECTIVE_WIRING_AUDIT_V2_OK
