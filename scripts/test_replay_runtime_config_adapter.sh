#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile src/scripts/replay_br_pipeline.py

grep -q "class ReplayRuntimeConfig" src/scripts/replay_br_pipeline.py
grep -q "def get_bool" src/scripts/replay_br_pipeline.py
grep -q "pipeline.runtime_config = ReplayRuntimeConfig()" src/scripts/replay_br_pipeline.py

echo "REPLAY_RUNTIME_CONFIG_ADAPTER_TEST_OK"
