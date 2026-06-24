#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core || exit 1

echo "=== TEST_GOLD_RUNTIME_SESSION_GUARD_APPLY_DRY_RUN_V1 ==="

python3 -m py_compile \
  src/scripts/research/build_gold_runtime_session_guard_apply_dry_run_v1.py

src/scripts/research/build_gold_runtime_session_guard_apply_dry_run_v1.py \
  | tee /tmp/gold_runtime_session_guard_apply_dry_run_v1.out

grep -q "GOLD_RUNTIME_SESSION_GUARD_APPLY_DRY_RUN_V1" /tmp/gold_runtime_session_guard_apply_dry_run_v1.out
grep -q "APPLY_ROW symbol=GDU6@RTSX guard_decision=ALLOW_RESEARCH_SHADOW" /tmp/gold_runtime_session_guard_apply_dry_run_v1.out
grep -q "APPLY_ROW symbol=GDU6@RTSX guard_decision=BLOCK_EVENING_SESSION" /tmp/gold_runtime_session_guard_apply_dry_run_v1.out
grep -q "APPLY_ROW symbol=GLU6@RTSX guard_decision=ALLOW_RESEARCH_SHADOW" /tmp/gold_runtime_session_guard_apply_dry_run_v1.out
grep -q "APPLY_ROW symbol=GLU6@RTSX guard_decision=BLOCK_EVENING_SESSION" /tmp/gold_runtime_session_guard_apply_dry_run_v1.out
grep -q "VERDICT=GOLD_RUNTIME_SESSION_GUARD_APPLY_DRY_RUN_READY" /tmp/gold_runtime_session_guard_apply_dry_run_v1.out

echo "TEST_GOLD_RUNTIME_SESSION_GUARD_APPLY_DRY_RUN_V1_OK"
