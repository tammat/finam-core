#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core || exit 1

echo "=== TEST_GOLD_FILTERED_EDGE_SCORECARD_8088_V1 ==="

python3 -m py_compile src/scripts/research/serve_multi_asset_breakout_dashboard_v1.py

sudo systemctl restart finam-multi-asset-breakout-dashboard.service
sleep 3

out=/tmp/gold_filtered_edge_scorecard_8088_v1.html
curl -fsS http://127.0.0.1:8088/ | tee "$out" >/dev/null

grep -q "Filtered Gold Edge" "$out"
grep -q "только сигналы до 19:00 МСК" "$out"
grep -q "GLU6@RTSX" "$out"
grep -q "GDU6@RTSX" "$out"
grep -q "PRIMARY" "$out"

echo "VERDICT=GOLD_FILTERED_EDGE_SCORECARD_8088_OK"
echo "TEST_GOLD_FILTERED_EDGE_SCORECARD_8088_V1_OK"
