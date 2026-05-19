#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile \
  src/scripts/runtime_anomaly_correlation.py

grep -q "RUNTIME_ANOMALY_CORRELATION_OK" \
  src/scripts/runtime_anomaly_correlation.py

grep -q "market anomalies detected" \
  src/scripts/runtime_anomaly_correlation.py

grep -q "runtime-anomaly-correlation.timer" \
  scripts/install_runtime_anomaly_correlation_timer.sh

echo "OK: runtime anomaly correlation"
