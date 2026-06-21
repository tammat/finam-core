#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_FUTURES_RELATIVE_STRENGTH_LAYER_V1 ==="

out="$(mktemp)"

python3 -m py_compile src/scripts/research/build_futures_relative_strength_layer_v1.py

PYTHONPATH=src \
RUNTIME_ALLOW_TRADING=0 \
EXECUTION_ENABLED=0 \
REAL_TRADING_ENABLED=0 \
python3 src/scripts/research/build_futures_relative_strength_layer_v1.py | tee "$out"

grep -q "VERDICT=FUTURES_RELATIVE_STRENGTH_LAYER_READY" "$out"
grep -q "TEST_FUTURES_RELATIVE_STRENGTH_LAYER_V1_OK" "$out"
grep -q "db_update=0" "$out"
grep -q "runtime_changed=0" "$out"
grep -q "execution_changed=0" "$out"
grep -q "telegram_send=0" "$out"

echo "VERDICT=FUTURES_RELATIVE_STRENGTH_LAYER_TEST_OK"
echo "TEST_FUTURES_RELATIVE_STRENGTH_LAYER_V1_OK"
