#!/usr/bin/env bash
set -euo pipefail

cd "$(git rev-parse --show-toplevel)"

echo "=== TEST NGQ6 FORWARD EXIT IDENTITY VERIFY V1 ==="

python3 -m py_compile src/scripts/research/build_ngq6_forward_exit_identity_verify_v1.py

python3 src/scripts/research/build_ngq6_forward_exit_identity_verify_v1.py \
  | tee /tmp/ngq6_forward_exit_identity_verify_v1.log

grep -q "NGQ6_FORWARD_EXIT_IDENTITY_VERIFY_V1_OK" /tmp/ngq6_forward_exit_identity_verify_v1.log
grep -q "VERDICT=" /tmp/ngq6_forward_exit_identity_verify_v1.log
grep -q "runtime_allow=0" /tmp/ngq6_forward_exit_identity_verify_v1.log
grep -q "execution_enabled=0" /tmp/ngq6_forward_exit_identity_verify_v1.log
grep -q "NGQ6_BAD_IDENTITY_ROWS=0" /tmp/ngq6_forward_exit_identity_verify_v1.log

echo TEST_NGQ6_FORWARD_EXIT_IDENTITY_VERIFY_V1_OK
