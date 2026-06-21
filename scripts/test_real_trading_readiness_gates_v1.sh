#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_REAL_TRADING_READINESS_GATES_V1 ==="

out="$(mktemp)"

PYTHONPATH=src \
RUNTIME_ALLOW_TRADING=0 \
EXECUTION_ENABLED=0 \
REAL_TRADING_ENABLED=0 \
python3 src/scripts/research/build_real_trading_readiness_gates_v1.py | tee "$out"

grep -q "TEST_REAL_TRADING_READINESS_GATES_V1_OK" "$out"
grep -q "runtime_allow=0" "$out"
grep -q "execution_enabled=0" "$out"
grep -q "real_trading_enabled=0" "$out"

echo "VERDICT=REAL_TRADING_READINESS_GATES_TEST_OK"
echo "TEST_REAL_TRADING_READINESS_GATES_V1_OK"
