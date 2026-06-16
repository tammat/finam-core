#!/usr/bin/env bash
set -euo pipefail

cd "$(git rev-parse --show-toplevel)"
export PYTHONPATH=src

python3 -m py_compile \
  src/scripts/runtime/build_trusted_pipeline_status_v1.py

python3 \
  src/scripts/runtime/build_trusted_pipeline_status_v1.py \
  | tee /tmp/trusted_pipeline_status_v1.log

grep -q "TRUSTED PIPELINE STATUS V1" \
  /tmp/trusted_pipeline_status_v1.log

grep -q "PIPELINE_STATUS" \
  /tmp/trusted_pipeline_status_v1.log

grep -q "TRUSTED_PIPELINE_STATUS_V1_OK" \
  /tmp/trusted_pipeline_status_v1.log

echo TEST_TRUSTED_PIPELINE_STATUS_V1_OK
