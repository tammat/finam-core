#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile \
  src/scripts/run_external_replay_pipeline.py \
  src/finam_core/replay/external_replay_adapter.py

python src/scripts/run_external_replay_pipeline.py --help >/dev/null

echo "OK: run_external_replay_pipeline compile"
