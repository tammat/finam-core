#!/usr/bin/env bash
set -euo pipefail

cd "$(git rev-parse --show-toplevel)"

echo "=== TEST FUTURES REAL BLOCK GUARD PROTECTIVE WIRING AUDIT V1 ==="
echo "runtime_allow=0"
echo "execution_enabled=0"

python3 -m py_compile \
  src/scripts/research/build_futures_real_block_guard_protective_wiring_audit_v1.py \
  src/finam_core/risk/futures_real_block_guard_v1.py \
  src/finam_core/execution/finam_order_client_adapter.py

python3 src/scripts/research/build_futures_real_block_guard_protective_wiring_audit_v1.py \
  | tee /tmp/futures_real_block_guard_protective_wiring_audit_v1.log

grep -q "FUTURES_REAL_BLOCK_GUARD_PROTECTIVE_WIRING_AUDIT_V1_OK" /tmp/futures_real_block_guard_protective_wiring_audit_v1.log
grep -q "VERDICT=" /tmp/futures_real_block_guard_protective_wiring_audit_v1.log
grep -q "runtime_allow=0" /tmp/futures_real_block_guard_protective_wiring_audit_v1.log
grep -q "execution_enabled=0" /tmp/futures_real_block_guard_protective_wiring_audit_v1.log

echo
echo "=== GUARD REQUIRED ROWS ==="
grep "GUARD_REQUIRED=" /tmp/futures_real_block_guard_protective_wiring_audit_v1.log || true

echo TEST_FUTURES_REAL_BLOCK_GUARD_PROTECTIVE_WIRING_AUDIT_V1_OK
