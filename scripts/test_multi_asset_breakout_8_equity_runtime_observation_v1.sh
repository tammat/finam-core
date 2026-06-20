#!/usr/bin/env bash
set -euo pipefail

echo "=== MULTI_ASSET_BREAKOUT_8_EQUITY_RUNTIME_OBSERVATION_V1 ==="

out="$(mktemp)"

python3 -m py_compile \
  src/scripts/research/build_multi_asset_breakout_8_equity_runtime_observation_v1.py

python3 \
  src/scripts/research/build_multi_asset_breakout_8_equity_runtime_observation_v1.py \
  | tee "$out"

grep -q "VERDICT=MULTI_ASSET_BREAKOUT_8_EQUITY_RUNTIME_OBSERVATION_READY" "$out"
grep -q "TEST_MULTI_ASSET_BREAKOUT_8_EQUITY_RUNTIME_OBSERVATION_V1_OK" "$out"

echo "VERDICT=MULTI_ASSET_BREAKOUT_8_EQUITY_RUNTIME_OBSERVATION_TEST_OK"
echo "TEST_MULTI_ASSET_BREAKOUT_8_EQUITY_RUNTIME_OBSERVATION_V1_OK"
