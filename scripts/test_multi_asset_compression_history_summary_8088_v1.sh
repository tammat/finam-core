#!/usr/bin/env bash
set -euo pipefail

echo "=== MULTI_ASSET_COMPRESSION_HISTORY_SUMMARY_8088_V1 ==="

html="$(curl -fsS http://127.0.0.1:8088/summary)"

echo "$html" | grep -q "Compression / Expansion"
echo "$html" | grep -q "snapshots:"
echo "$html" | grep -q "history rows:"
echo "$html" | grep -q "compression rows:"
echo "$html" | grep -q "expansion rows:"

echo "VERDICT=MULTI_ASSET_COMPRESSION_HISTORY_SUMMARY_8088_OK"
echo "TEST_MULTI_ASSET_COMPRESSION_HISTORY_SUMMARY_8088_V1_OK"
