#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile \
  src/scripts/run_external_replay_pipeline.py \
  src/finam_core/runtime/runtime_adaptive_risk.py \
  src/finam_core/research/research_regime_classifier.py

python src/scripts/run_external_replay_pipeline.py --help >/dev/null

echo "OK: runtime adaptive risk integration"
