#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile \
  src/finam_core/pipelines/paper_pipeline.py \
  src/finam_core/analytics/trade_context_snapshot_repository.py

grep -q "_save_trade_context_snapshot_for_paper_trade" src/finam_core/pipelines/paper_pipeline.py
grep -q "TRADE_CONTEXT_SNAPSHOT_SAVED" src/finam_core/pipelines/paper_pipeline.py
grep -q "TRADE_CONTEXT_SNAPSHOT_ENABLED" src/finam_core/pipelines/paper_pipeline.py

echo "PAPER_TRADE_CONTEXT_SNAPSHOT_COMPILE_OK"
