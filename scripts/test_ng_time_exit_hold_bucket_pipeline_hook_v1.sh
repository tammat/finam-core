#!/usr/bin/env bash
set -euo pipefail

ROOT="$(git rev-parse --show-toplevel)"
cd "$ROOT"
export PYTHONPATH=src

python3 -m py_compile \
  src/finam_core/governance/ng_time_exit_hold_bucket_policy_v1.py \
  src/finam_core/pipelines/paper_pipeline.py

grep -q "NgTimeExitHoldBucketPolicyV1" src/finam_core/pipelines/paper_pipeline.py
grep -q "ENABLE_NG_TIME_EXIT_HOLD_BUCKET_POLICY_V1" src/finam_core/pipelines/paper_pipeline.py
grep -q "PIPE_NG_TIME_EXIT_HOLD_BUCKET_POLICY_V1" src/finam_core/pipelines/paper_pipeline.py
grep -q "PIPE_NG_TIME_EXIT_HOLD_BUCKET_BLOCK_V1" src/finam_core/pipelines/paper_pipeline.py
grep -q "ng_time_exit_hold_bucket_pipeline_hook_v1_call" src/finam_core/pipelines/paper_pipeline.py

./scripts/test_ng_time_exit_hold_bucket_policy_v1.sh

echo TEST_NG_TIME_EXIT_HOLD_BUCKET_PIPELINE_HOOK_V1_OK
