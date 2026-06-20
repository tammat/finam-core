#!/usr/bin/env bash
set -euo pipefail

echo "=== MULTI_ASSET_BREAKOUT_EDGE_SCORECARD_8_EQUITIES_V1 ==="

out="$(mktemp)"

python3 -m py_compile src/scripts/research/build_multi_asset_breakout_edge_scorecard_8_equities_v1.py

python3 src/scripts/research/build_multi_asset_breakout_edge_scorecard_8_equities_v1.py | tee "$out"

grep -q "VERDICT=MULTI_ASSET_BREAKOUT_EDGE_SCORECARD_8_EQUITIES_READY" "$out"
grep -q "TEST_MULTI_ASSET_BREAKOUT_EDGE_SCORECARD_8_EQUITIES_V1_OK" "$out"
grep -q '"db_update": 0' "$out"
grep -q '"runtime_changed": 0' "$out"
grep -q '"execution_changed": 0' "$out"
grep -q '"runtime_equities": 8' "$out"

echo "VERDICT=MULTI_ASSET_BREAKOUT_EDGE_SCORECARD_8_EQUITIES_TEST_OK"
echo "TEST_MULTI_ASSET_BREAKOUT_EDGE_SCORECARD_8_EQUITIES_V1_OK"
