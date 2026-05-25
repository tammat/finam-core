#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile \
  src/finam_core/pipelines/paper_pipeline.py \
  src/scripts/replay_br_pipeline.py

grep -q "if atr_pct <= 0:" src/finam_core/pipelines/paper_pipeline.py
grep -q 'features\["atr_pct"\] = atr_pct' src/finam_core/pipelines/paper_pipeline.py

echo "BR_REPLAY_ATR_LOCAL_FALLBACK_TEST_OK"
