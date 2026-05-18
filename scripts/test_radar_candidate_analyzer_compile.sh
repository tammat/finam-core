#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile \
  src/scripts/analyze_radar_candidates.py

echo "OK: radar candidate analyzer compile"
