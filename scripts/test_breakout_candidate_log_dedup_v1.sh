#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core
export PYTHONPATH=src

echo "TEST_BREAKOUT_CANDIDATE_LOG_DEDUP_V1_START"

python -m py_compile src/finam_core/pipelines/paper_pipeline.py

grep -q "def _log_breakout_detected_dedup_v1(" src/finam_core/pipelines/paper_pipeline.py
grep -q "_breakout_detected_log_cache_v1" src/finam_core/pipelines/paper_pipeline.py
grep -q "PIPE_BREAKOUT_DEDUP_TTL_SEC" src/finam_core/pipelines/paper_pipeline.py

grep -q '_log_breakout_detected_dedup_v1(str(sym), "BUY", local_high)' \
  src/finam_core/pipelines/paper_pipeline.py

grep -q '_log_breakout_detected_dedup_v1(str(sym), "SELL", local_low)' \
  src/finam_core/pipelines/paper_pipeline.py

echo "TEST_BREAKOUT_CANDIDATE_LOG_DEDUP_V1_OK"
