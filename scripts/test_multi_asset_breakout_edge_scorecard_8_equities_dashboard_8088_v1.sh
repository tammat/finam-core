#!/usr/bin/env bash
set -euo pipefail

echo "=== MULTI_ASSET_BREAKOUT_EDGE_SCORECARD_8_EQUITIES_DASHBOARD_8088_V1 ==="

api="$(curl -fsS http://127.0.0.1:8088/api/current)"
html="$(curl -fsS http://127.0.0.1:8088/edge)"

echo "$api" | jq -e '.summary.equity_rows == "8"'
echo "$api" | jq -e '.edge_scorecard.runtime_equities == 8'
echo "$api" | jq -e '.edge_scorecard.scorecard_rows == 8'
echo "$api" | jq -e '.edge_scorecard.top_edge_symbol != null'

echo "$html" | grep -q "Edge Scorecard 8 equities V1"
echo "$html" | grep -q "SBER@MISX"
echo "$html" | grep -q "PLZL@MISX"
echo "$html" | grep -q "Edge score"

echo "VERDICT=MULTI_ASSET_BREAKOUT_EDGE_SCORECARD_8_EQUITIES_DASHBOARD_8088_OK"
echo "TEST_MULTI_ASSET_BREAKOUT_EDGE_SCORECARD_8_EQUITIES_DASHBOARD_8088_V1_OK"
