#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core || exit 1

echo "=== TEST_GOLD_RUNTIME_SESSION_GUARD_IMPLEMENTATION_DRY_RUN_V1 ==="

python3 -m py_compile \
  src/scripts/research/build_gold_runtime_session_guard_implementation_dry_run_v1.py

src/scripts/research/build_gold_runtime_session_guard_implementation_dry_run_v1.py \
  | tee /tmp/gold_runtime_session_guard_implementation_dry_run_v1.out

grep -q "GOLD_RUNTIME_SESSION_GUARD_IMPLEMENTATION_DRY_RUN_V1" \
  /tmp/gold_runtime_session_guard_implementation_dry_run_v1.out

grep -q "TARGET_MATCH line=4376" \
  /tmp/gold_runtime_session_guard_implementation_dry_run_v1.out

grep -q "insert_before_target=routed = self.signal_intent_router.route(raw_intent)" \
  /tmp/gold_runtime_session_guard_implementation_dry_run_v1.out

grep -q "PIPE_RUNTIME_GOLD_SESSION_BLOCK" \
  /tmp/gold_runtime_session_guard_implementation_dry_run_v1.out

grep -q "block_reason=gold_evening_session" \
  /tmp/gold_runtime_session_guard_implementation_dry_run_v1.out

grep -q "paper_pipeline_modified=0" \
  /tmp/gold_runtime_session_guard_implementation_dry_run_v1.out

grep -q "VERDICT=GOLD_RUNTIME_SESSION_GUARD_IMPLEMENTATION_DRY_RUN_READY" \
  /tmp/gold_runtime_session_guard_implementation_dry_run_v1.out

echo "TEST_GOLD_RUNTIME_SESSION_GUARD_IMPLEMENTATION_DRY_RUN_V1_OK"
