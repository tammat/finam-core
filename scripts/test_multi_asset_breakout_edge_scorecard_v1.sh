#!/usr/bin/env bash
set -euo pipefail

echo "=== MULTI_ASSET_BREAKOUT_EDGE_SCORECARD_V1 ==="

out="$(mktemp)"
python src/scripts/research/build_multi_asset_breakout_edge_scorecard_v1.py | tee "$out"

grep -q "VERDICT=MULTI_ASSET_BREAKOUT_EDGE_SCORECARD_READY" "$out"
grep -q "TEST_MULTI_ASSET_BREAKOUT_EDGE_SCORECARD_V1_OK" "$out"

if grep -q '"db_update": 1' "$out"; then
  echo "VERDICT=EDGE_SCORECARD_UNEXPECTED_DB_UPDATE"
  exit 1
fi

if grep -q '"execution_changed": 1' "$out"; then
  echo "VERDICT=EDGE_SCORECARD_UNEXPECTED_EXECUTION_CHANGE"
  exit 1
fi

if grep -q '"telegram_send": 1' "$out"; then
  echo "VERDICT=EDGE_SCORECARD_UNEXPECTED_TELEGRAM_SEND"
  exit 1
fi

echo "VERDICT=MULTI_ASSET_BREAKOUT_EDGE_SCORECARD_TEST_OK"
echo "TEST_MULTI_ASSET_BREAKOUT_EDGE_SCORECARD_V1_OK"
