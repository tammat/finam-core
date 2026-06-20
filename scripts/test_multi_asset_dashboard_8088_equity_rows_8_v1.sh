#!/usr/bin/env bash
set -euo pipefail

echo "=== MULTI_ASSET_DASHBOARD_8088_EQUITY_ROWS_8_V1 ==="

summary="$(curl -fsS http://127.0.0.1:8088/api/current | jq -r '.summary')"

echo "$summary"

echo "$summary" | jq -e '.equity_rows == "8"'
echo "$summary" | jq -e '.universe_total == "8"'

echo "VERDICT=MULTI_ASSET_DASHBOARD_8088_EQUITY_ROWS_8_OK"
echo "TEST_MULTI_ASSET_DASHBOARD_8088_EQUITY_ROWS_8_V1_OK"
