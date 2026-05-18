#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile src/scripts/analyze_watch_candidates_runtime.py

echo "OK: watch candidate runtime analyzer compile"
