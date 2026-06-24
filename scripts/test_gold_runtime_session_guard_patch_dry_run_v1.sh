#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core || exit 1

echo "=== TEST_GOLD_RUNTIME_SESSION_GUARD_PATCH_DRY_RUN_V1 ==="

python3 -m py_compile \
  src/scripts/research/build_gold_runtime_session_guard_patch_dry_run_v1.py

src/scripts/research/build_gold_runtime_session_guard_patch_dry_run_v1.py \
  | tee /tmp/gold_runtime_session_guard_patch_dry_run_v1.out

grep -q "GOLD_RUNTIME_SESSION_GUARD_PATCH_DRY_RUN_V1" \
  /tmp/gold_runtime_session_guard_patch_dry_run_v1.out

grep -q "PATCH_CANDIDATE" \
  /tmp/gold_runtime_session_guard_patch_dry_run_v1.out

grep -q "BLOCK_EVENING_SESSION" \
  /tmp/gold_runtime_session_guard_patch_dry_run_v1.out

grep -q "block_reason=gold_evening_session" \
  /tmp/gold_runtime_session_guard_patch_dry_run_v1.out

grep -q "paper_pipeline_modified=0" \
  /tmp/gold_runtime_session_guard_patch_dry_run_v1.out

grep -q "VERDICT=GOLD_RUNTIME_SESSION_GUARD_PATCH_DRY_RUN_READY" \
  /tmp/gold_runtime_session_guard_patch_dry_run_v1.out

echo "TEST_GOLD_RUNTIME_SESSION_GUARD_PATCH_DRY_RUN_V1_OK"
