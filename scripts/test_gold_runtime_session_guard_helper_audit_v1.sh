#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core || exit 1

echo "=== TEST_GOLD_RUNTIME_SESSION_GUARD_HELPER_AUDIT_V1 ==="

python3 -m py_compile \
  src/scripts/research/build_gold_runtime_session_guard_helper_audit_v1.py

src/scripts/research/build_gold_runtime_session_guard_helper_audit_v1.py \
  | tee /tmp/gold_runtime_session_guard_helper_audit_v1.out

grep -q "GOLD_RUNTIME_SESSION_GUARD_HELPER_AUDIT_V1" \
  /tmp/gold_runtime_session_guard_helper_audit_v1.out

grep -q "HELPER_HIT" \
  /tmp/gold_runtime_session_guard_helper_audit_v1.out

grep -q "VERDICT=GOLD_RUNTIME_SESSION_GUARD_HELPER_AUDIT_READY" \
  /tmp/gold_runtime_session_guard_helper_audit_v1.out

echo "TEST_GOLD_RUNTIME_SESSION_GUARD_HELPER_AUDIT_V1_OK"
