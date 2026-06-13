#!/usr/bin/env bash
set -euo pipefail

ROOT="$(git rev-parse --show-toplevel)"
cd "$ROOT"

export PYTHONPATH=src

python3 -m py_compile \
  src/scripts/analytics/build_runtime_edge_failure_analysis_v1.py

python3 src/scripts/analytics/build_runtime_edge_failure_analysis_v1.py \
  | tee /tmp/runtime_edge_failure_analysis_v1.log

grep -q "RUNTIME EDGE FAILURE ANALYSIS V1" \
  /tmp/runtime_edge_failure_analysis_v1.log

grep -q "VERDICT=" \
  /tmp/runtime_edge_failure_analysis_v1.log

echo TEST_RUNTIME_EDGE_FAILURE_ANALYSIS_V1_OK
