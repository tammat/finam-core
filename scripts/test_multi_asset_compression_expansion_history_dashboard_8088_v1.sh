#!/usr/bin/env bash
set -euo pipefail

echo "=== MULTI_ASSET_COMPRESSION_EXPANSION_HISTORY_DASHBOARD_8088_V1 ==="

api="$(curl -fsS http://127.0.0.1:8088/api/current)"
html="$(curl -fsS http://127.0.0.1:8088/compression-history)"

echo "$api" | jq -e '.compression_history.verdict == "MULTI_ASSET_COMPRESSION_EXPANSION_HISTORY_DASHBOARD_READY"'
echo "$api" | jq -e '.compression_history.snapshots >= 1'
echo "$api" | jq -e '.compression_history.rows >= 30'
echo "$api" | jq -e '.compression_history.expansion_rows >= 1'
echo "$api" | jq -e '.compression_history.compression_rows >= 1'

echo "$html" | grep -q "Compression / Expansion History V1"
echo "$html" | grep -q "BRQ6@RTSX"
echo "$html" | grep -q "PLZL@MISX"
echo "$html" | grep -q "Expansion hits"

echo "VERDICT=MULTI_ASSET_COMPRESSION_EXPANSION_HISTORY_DASHBOARD_8088_OK"
echo "TEST_MULTI_ASSET_COMPRESSION_EXPANSION_HISTORY_DASHBOARD_8088_V1_OK"
