#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_MONDAY_PAPER_STARTUP_READINESS_V1 ==="

out="$(mktemp)"

python3 -m py_compile src/scripts/research/build_monday_paper_startup_readiness_v1.py

PYTHONPATH=src \
RUNTIME_ALLOW_TRADING=0 \
EXECUTION_ENABLED=0 \
REAL_TRADING_ENABLED=0 \
python3 src/scripts/research/build_monday_paper_startup_readiness_v1.py | tee "$out"

grep -q "TEST_MONDAY_PAPER_STARTUP_READINESS_V1_OK" "$out"
grep -q "runtime_allow_trading=0" "$out"
grep -q "execution_enabled=0" "$out"
grep -q "real_trading_enabled=0" "$out"
grep -q "failures=NONE" "$out"
grep -q "VERDICT=MONDAY_PAPER_STARTUP_READY" "$out"

echo "VERDICT=MONDAY_PAPER_STARTUP_READINESS_TEST_OK"
echo "TEST_MONDAY_PAPER_STARTUP_READINESS_V1_OK"
