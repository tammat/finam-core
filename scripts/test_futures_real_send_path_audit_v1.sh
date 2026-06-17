#!/usr/bin/env bash
set -euo pipefail

cd "$(git rev-parse --show-toplevel)"

echo "=== TEST FUTURES REAL SEND PATH AUDIT V1 ==="

python3 -m py_compile src/scripts/research/build_futures_real_send_path_audit_v1.py
python3 -m py_compile src/finam_core/risk/futures_real_block_guard_v1.py

python3 src/scripts/research/build_futures_real_send_path_audit_v1.py \
  | tee /tmp/futures_real_send_path_audit_v1.log

grep -q "FUTURES_REAL_SEND_PATH_AUDIT_V1_OK" /tmp/futures_real_send_path_audit_v1.log
grep -q "VERDICT=" /tmp/futures_real_send_path_audit_v1.log
grep -q "PRIMARY_CANDIDATE" /tmp/futures_real_send_path_audit_v1.log
grep -q "runtime_allow=0" /tmp/futures_real_send_path_audit_v1.log
grep -q "execution_enabled=0" /tmp/futures_real_send_path_audit_v1.log

echo
echo "=== PRIMARY SEND PATH CANDIDATES ==="
grep "PRIMARY_CANDIDATE" /tmp/futures_real_send_path_audit_v1.log

echo TEST_FUTURES_REAL_SEND_PATH_AUDIT_V1_OK
