#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH="${PYTHONPATH:-src}"

python -m py_compile src/scripts/run_ng_replay_expansion.py

grep -q "NG_REPLAY_EXPANSION_OK" src/scripts/run_ng_replay_expansion.py

echo "TEST_NG_REPLAY_EXPANSION_OK"
