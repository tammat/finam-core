#!/usr/bin/env bash
set -euo pipefail

echo "=== MULTI_ASSET_COMPRESSION_EXPANSION_WATCH_V1 ==="

out="$(mktemp)"

python3 -m py_compile src/scripts/research/build_multi_asset_compression_expansion_watch_v1.py
python3 src/scripts/research/build_multi_asset_compression_expansion_watch_v1.py | tee "$out"

grep -q "VERDICT=MULTI_ASSET_COMPRESSION_EXPANSION_WATCH_READY" "$out"
grep -q "TEST_MULTI_ASSET_COMPRESSION_EXPANSION_WATCH_V1_OK" "$out"
grep -q '"db_update": 0' "$out"
grep -q '"runtime_changed": 0' "$out"
grep -q '"execution_changed": 0' "$out"
grep -q '"telegram_send": 0' "$out"

echo "VERDICT=MULTI_ASSET_COMPRESSION_EXPANSION_WATCH_TEST_OK"
echo "TEST_MULTI_ASSET_COMPRESSION_EXPANSION_WATCH_V1_OK"
