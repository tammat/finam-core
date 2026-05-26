#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile src/finam_core/pipelines/paper_pipeline.py

grep -q "runtime_override_bypassed_for_replay" src/finam_core/pipelines/paper_pipeline.py
grep -q "RUNTIME_OVERRIDE_GATE_ENABLED" src/finam_core/pipelines/paper_pipeline.py
grep -q "REPLAY_DISABLE_RUNTIME_CONTROL" src/finam_core/pipelines/paper_pipeline.py

echo "RUNTIME_OVERRIDE_REPLAY_BYPASS_COMPILE_OK"
