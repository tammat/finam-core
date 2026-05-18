#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile src/scripts/replay_batch_summary.py
python src/scripts/replay_batch_summary.py --help >/dev/null

echo "OK: replay_batch_summary compile"
