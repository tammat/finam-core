#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core || exit 1

echo "=== TEST_GOLD_RUNTIME_SESSION_GUARD_CALLSITE_AUDIT_V1 ==="

python3 -m py_compile \
  src/scripts/research/build_gold_runtime_session_guard_callsite_audit_v1.py

src/scripts/research/build_gold_runtime_session_guard_callsite_audit_v1.py \
  | tee /tmp/gold_runtime_session_guard_callsite_audit_v1.out

grep -q "GOLD_RUNTIME_SESSION_GUARD_CALLSITE_AUDIT_V1" /tmp/gold_runtime_session_guard_callsite_audit_v1.out
grep -q "CALLSITE_ROW file=src/finam_core/pipelines/paper_pipeline.py status=FOUND" /tmp/gold_runtime_session_guard_callsite_audit_v1.out
grep -q "preferred_file=src/finam_core/pipelines/paper_pipeline.py" /tmp/gold_runtime_session_guard_callsite_audit_v1.out
grep -q "decision=BLOCK_EVENING_SESSION" /tmp/gold_runtime_session_guard_callsite_audit_v1.out
grep -q "do_not_touch_execution_layer=1" /tmp/gold_runtime_session_guard_callsite_audit_v1.out
grep -q "do_not_touch_real_orders=1" /tmp/gold_runtime_session_guard_callsite_audit_v1.out
grep -q "VERDICT=GOLD_RUNTIME_SESSION_GUARD_CALLSITE_AUDIT_READY" /tmp/gold_runtime_session_guard_callsite_audit_v1.out

echo "TEST_GOLD_RUNTIME_SESSION_GUARD_CALLSITE_AUDIT_V1_OK"
