#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile src/scripts/analyze_watch_candidates_runtime.py

grep -q "signal_correlation_groups" src/scripts/analyze_watch_candidates_runtime.py
grep -q "MAX_ALERTS_PER_CORRELATION_GROUP" src/scripts/analyze_watch_candidates_runtime.py

echo "OK: correlation exposure filter"
