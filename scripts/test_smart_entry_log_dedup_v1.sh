#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core
export PYTHONPATH=src

echo "TEST_SMART_ENTRY_LOG_DEDUP_V1_START"

python -m py_compile src/finam_core/pipelines/paper_pipeline.py

grep -q 'PIPE_SMART_ENTRY_LOG_TTL_SEC' src/finam_core/pipelines/paper_pipeline.py
grep -q 'PIPE_SMART_ENTRY BUY symbol=' src/finam_core/pipelines/paper_pipeline.py
grep -q 'PIPE_SMART_ENTRY SELL symbol=' src/finam_core/pipelines/paper_pipeline.py

echo "TEST_SMART_ENTRY_LOG_DEDUP_V1_OK"
