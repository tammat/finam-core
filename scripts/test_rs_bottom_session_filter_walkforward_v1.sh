#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core || exit 1

echo "=== TEST_RS_BOTTOM_SESSION_FILTER_WALKFORWARD_V1 ==="

python3 -m py_compile src/scripts/research/build_rs_bottom_session_filter_walkforward_v1.py

out="/tmp/rs_bottom_session_filter_walkforward_v1.log"
python3 src/scripts/research/build_rs_bottom_session_filter_walkforward_v1.py | tee "$out"

grep -q "WALKFORWARD_BY_DAY" "$out"
grep -q "WALKFORWARD_BY_SYMBOL" "$out"
grep -q "WALKFORWARD_BY_HOUR_MSK" "$out"
grep -q "EQUITY_CURVE_SUMMARY" "$out"
grep -q "WALKFORWARD_SUMMARY" "$out"
grep -q "VERDICT=RS_BOTTOM_SESSION_FILTER_WALKFORWARD_" "$out"

echo "TEST_RS_BOTTOM_SESSION_FILTER_WALKFORWARD_V1_OK"
