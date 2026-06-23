#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core || exit 1

echo "=== TEST_RS_BOTTOM_ACTIVE_FUTURES_UNIVERSE_V1 ==="

python3 -m py_compile src/scripts/research/build_rs_bottom_active_futures_universe_v1.py

out="/tmp/rs_bottom_active_futures_universe_v1.log"
python3 src/scripts/research/build_rs_bottom_active_futures_universe_v1.py | tee "$out"

grep -q "ACTIVE_FUTURES_ROWS" "$out"
grep -q "ACTIVE_FUTURES_UNIVERSE_SUMMARY" "$out"
grep -q "VERDICT=RS_BOTTOM_ACTIVE_FUTURES_UNIVERSE_READY" "$out"

echo "TEST_RS_BOTTOM_ACTIVE_FUTURES_UNIVERSE_V1_OK"
