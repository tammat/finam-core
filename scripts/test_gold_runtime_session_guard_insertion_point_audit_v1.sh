#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core || exit 1

echo "=== TEST_GOLD_RUNTIME_SESSION_GUARD_INSERTION_POINT_AUDIT_V1 ==="

python3 -m py_compile \
  src/scripts/research/build_gold_runtime_session_guard_insertion_point_audit_v1.py

src/scripts/research/build_gold_runtime_session_guard_insertion_point_audit_v1.py \
  | tee /tmp/gold_runtime_session_guard_insertion_point_audit_v1.out

grep -q "INSERTION_POINT" \
  /tmp/gold_runtime_session_guard_insertion_point_audit_v1.out

grep -q "OPTION_A" \
  /tmp/gold_runtime_session_guard_insertion_point_audit_v1.out

grep -q "OPTION_B" \
  /tmp/gold_runtime_session_guard_insertion_point_audit_v1.out

grep -q "preferred=OPTION_B" \
  /tmp/gold_runtime_session_guard_insertion_point_audit_v1.out

grep -q "VERDICT=GOLD_RUNTIME_SESSION_GUARD_INSERTION_POINT_READY" \
  /tmp/gold_runtime_session_guard_insertion_point_audit_v1.out

echo "TEST_GOLD_RUNTIME_SESSION_GUARD_INSERTION_POINT_AUDIT_V1_OK"
