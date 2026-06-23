#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core || exit 1

echo "=== TEST_RS_BOTTOM_SESSION_FILTER_REPLAY_V1 ==="

python3 -m py_compile src/scripts/research/build_rs_bottom_session_filter_replay_v1.py

out="/tmp/rs_bottom_session_filter_replay_v1.log"
python3 src/scripts/research/build_rs_bottom_session_filter_replay_v1.py | tee "$out"

grep -q "REPLAY_SUMMARY" "$out"
grep -q "EQUITY_CURVE_SUMMARY" "$out"
grep -q "VERDICT=RS_BOTTOM_SESSION_FILTER_REPLAY_" "$out"

echo "TEST_RS_BOTTOM_SESSION_FILTER_REPLAY_V1_OK"
