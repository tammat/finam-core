#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_EDGE_STABILITY_REPORT_V1 ==="

python3 -m py_compile \
  src/scripts/research/build_edge_stability_report_v1.py

python3 \
  src/scripts/research/build_edge_stability_report_v1.py \
  | tee /tmp/edge_stability_report_v1.log

grep -q "VERDICT=EDGE_STABILITY_REPORT_READY" \
  /tmp/edge_stability_report_v1.log

grep -q "EDGE_VERDICT" \
  /tmp/edge_stability_report_v1.log

echo "VERDICT=EDGE_STABILITY_REPORT_TEST_OK"
echo "TEST_EDGE_STABILITY_REPORT_V1_OK"
