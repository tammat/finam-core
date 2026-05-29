#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core
export PYTHONPATH=src

echo "TEST_BREAKOUT_CANDIDATE_LOG_DEDUP_V2_START"

python -m py_compile src/finam_core/pipelines/paper_pipeline.py

grep -q 'key = f"{symbol}:{str(side).upper()}"' \
  src/finam_core/pipelines/paper_pipeline.py

grep -q 'v2: dedup по instrument+side' \
  src/finam_core/pipelines/paper_pipeline.py

grep -q "PIPE_BREAKOUT_DEDUP_TTL_SEC" \
  src/finam_core/pipelines/paper_pipeline.py

echo "TEST_BREAKOUT_CANDIDATE_LOG_DEDUP_V2_OK"
