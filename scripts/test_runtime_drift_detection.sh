#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile \
  src/scripts/runtime_drift_detection.py

grep -q "RUNTIME_DRIFT_DETECTED" \
  src/scripts/runtime_drift_detection.py

grep -q "runtime watchlist empty" \
  src/scripts/runtime_drift_detection.py

grep -q "runtime-drift-detection.timer" \
  scripts/install_runtime_drift_detection_timer.sh

echo "OK: runtime drift detection"
