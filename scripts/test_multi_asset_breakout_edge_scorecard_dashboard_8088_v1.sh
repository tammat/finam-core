#!/usr/bin/env bash
set -euo pipefail

echo "=== MULTI_ASSET_BREAKOUT_EDGE_SCORECARD_DASHBOARD_8088_V1 ==="

python3 -m py_compile \
  src/scripts/research/build_multi_asset_breakout_edge_scorecard_v1.py \
  src/scripts/research/serve_multi_asset_breakout_dashboard_v1.py

api="$(curl -fsS http://127.0.0.1:8088/api/current)"
page="$(curl -fsS http://127.0.0.1:8088/edge)"

echo "$api" | grep -q '"edge_scorecard"'
echo "$api" | grep -q 'MULTI_ASSET_BREAKOUT_EDGE_SCORECARD_READY'
echo "$page" | grep -q 'Edge Scorecard V1'
echo "$page" | grep -q 'Статус Edge'

echo "VERDICT=MULTI_ASSET_BREAKOUT_EDGE_SCORECARD_DASHBOARD_8088_OK"
echo "TEST_MULTI_ASSET_BREAKOUT_EDGE_SCORECARD_DASHBOARD_8088_V1_OK"
