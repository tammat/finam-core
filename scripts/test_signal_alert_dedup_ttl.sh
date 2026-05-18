#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile src/scripts/analyze_watch_candidates_runtime.py

grep -q "signal_alert_dedup" src/scripts/analyze_watch_candidates_runtime.py
grep -q "SIGNAL_ALERT_TTL_MINUTES" src/scripts/analyze_watch_candidates_runtime.py

echo "OK: signal alert dedup ttl"
