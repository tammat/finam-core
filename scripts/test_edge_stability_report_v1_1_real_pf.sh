#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_EDGE_STABILITY_REPORT_V1_1_REAL_PF ==="

python3 -m py_compile src/scripts/research/build_edge_stability_report_v1_1_real_pf.py

python3 src/scripts/research/build_edge_stability_report_v1_1_real_pf.py \
  | tee /tmp/edge_stability_report_v1_1_real_pf.log

grep -q "VERDICT=EDGE_STABILITY_REPORT_V1_1_REAL_PF_READY" /tmp/edge_stability_report_v1_1_real_pf.log
grep -q "TEST_EDGE_STABILITY_REPORT_V1_1_REAL_PF_OK" /tmp/edge_stability_report_v1_1_real_pf.log
grep -q "real_pf=" /tmp/edge_stability_report_v1_1_real_pf.log
grep -q "positive_sum=" /tmp/edge_stability_report_v1_1_real_pf.log
grep -q "negative_sum=" /tmp/edge_stability_report_v1_1_real_pf.log
grep -q "EDGE_VERDICT" /tmp/edge_stability_report_v1_1_real_pf.log

echo "VERDICT=EDGE_STABILITY_REPORT_V1_1_REAL_PF_TEST_OK"
echo "TEST_EDGE_STABILITY_REPORT_V1_1_REAL_PF_OK"
