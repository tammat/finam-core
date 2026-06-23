#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core || exit 1

echo "=== TEST_RS_BOTTOM_FAMILY_STABILITY_V1 ==="

python3 -m py_compile src/scripts/research/build_rs_bottom_family_stability_v1.py

out="/tmp/rs_bottom_family_stability_v1.log"
python3 src/scripts/research/build_rs_bottom_family_stability_v1.py | tee "$out"

grep -q "FAMILY_ROWS" "$out"
grep -q "SYMBOL_ROWS" "$out"
grep -q "FAMILY_STABILITY_SUMMARY" "$out"
grep -q "VERDICT=RS_BOTTOM_FAMILY_STABILITY_" "$out"

echo "TEST_RS_BOTTOM_FAMILY_STABILITY_V1_OK"
