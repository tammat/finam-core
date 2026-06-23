#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core || exit 1

echo "=== TEST_RS_BOTTOM_SESSION_FILTER_STABILITY_V1 ==="

python3 -m py_compile \
  src/scripts/research/build_rs_bottom_session_filter_stability_v1.py

python3 \
  src/scripts/research/build_rs_bottom_session_filter_stability_v1.py \
  | tee /tmp/rs_bottom_session_filter_stability_v1.log

grep -q "STABILITY_SUMMARY" \
  /tmp/rs_bottom_session_filter_stability_v1.log

grep -q "VERDICT=RS_BOTTOM_SESSION_FILTER_STABILITY_" \
  /tmp/rs_bottom_session_filter_stability_v1.log

echo "TEST_RS_BOTTOM_SESSION_FILTER_STABILITY_V1_OK"
