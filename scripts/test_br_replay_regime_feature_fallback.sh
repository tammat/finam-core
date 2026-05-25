#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile \
  src/finam_core/pipelines/paper_pipeline.py \
  src/scripts/replay_br_pipeline.py

grep -q "replay-бар не всегда содержит feature payload" src/finam_core/pipelines/paper_pipeline.py
grep -q 'features\["atr_pct"\]' src/finam_core/pipelines/paper_pipeline.py
grep -q "compression_ratio = 1.0" src/finam_core/pipelines/paper_pipeline.py

echo "BR_REPLAY_REGIME_FEATURE_FALLBACK_TEST_OK"
