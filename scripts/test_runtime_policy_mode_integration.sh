#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile \
  src/scripts/run_external_replay_pipeline.py \
  src/finam_core/runtime/runtime_policy_mode_resolver.py \
  src/finam_core/runtime/active_policy_reader.py

echo "OK: runtime policy mode integration"
