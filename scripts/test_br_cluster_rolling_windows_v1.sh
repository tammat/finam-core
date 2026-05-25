#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile \
  src/scripts/research/build_br_cluster_rolling_windows_v1.py

grep -q "WINDOW_SIZE = 20" \
  src/scripts/research/build_br_cluster_rolling_windows_v1.py

grep -q "REGIME_EDGE_STABLE" \
  src/scripts/research/build_br_cluster_rolling_windows_v1.py

grep -q "REGIME_EDGE_TRANSITION" \
  src/scripts/research/build_br_cluster_rolling_windows_v1.py

grep -q "REGIME_EDGE_UNSTABLE" \
  src/scripts/research/build_br_cluster_rolling_windows_v1.py

grep -q "BR_CLUSTER_ROLLING_WINDOWS_V1_OK" \
  src/scripts/research/build_br_cluster_rolling_windows_v1.py

echo "BR_CLUSTER_ROLLING_WINDOWS_V1_TEST_OK"
