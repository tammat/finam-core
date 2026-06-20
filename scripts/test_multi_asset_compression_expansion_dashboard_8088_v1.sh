#!/usr/bin/env bash
set -euo pipefail

echo "=== MULTI_ASSET_COMPRESSION_EXPANSION_DASHBOARD_8088_V1 ==="

api="$(curl -fsS http://127.0.0.1:8088/api/current)"
html="$(curl -fsS http://127.0.0.1:8088/compression)"

echo "$api" | jq -e '.compression_expansion.verdict == "MULTI_ASSET_COMPRESSION_EXPANSION_WATCH_READY"'
echo "$api" | jq -e '.compression_expansion.rows_total >= 1'
echo "$api" | jq -e '.compression_expansion.equities_total == 8'
echo "$api" | jq -e '.compression_expansion.indexes_total == 2'

echo "$html" | grep -q "Compression / Expansion Watch V1"
echo "$html" | grep -q "EXPANSION_CANDIDATE"
echo "$html" | grep -q "COMPRESSION"
echo "$html" | grep -q "PLZL@MISX"

echo "VERDICT=MULTI_ASSET_COMPRESSION_EXPANSION_DASHBOARD_8088_OK"
echo "TEST_MULTI_ASSET_COMPRESSION_EXPANSION_DASHBOARD_8088_V1_OK"
