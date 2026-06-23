#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_EQUITY_NO_BARS_DIAGNOSTIC_V2 ==="

out="$(mktemp)"

python3 -m py_compile \
src/scripts/research/build_equity_no_bars_diagnostic_v2.py

PYTHONPATH=src \
RUNTIME_ALLOW_TRADING=0 \
EXECUTION_ENABLED=0 \
REAL_TRADING_ENABLED=0 \
python3 src/scripts/research/build_equity_no_bars_diagnostic_v2.py | tee "$out"

grep -q "TEST_EQUITY_NO_BARS_DIAGNOSTIC_V2_OK" "$out"
grep -q "runtime_equities=" "$out"
grep -q "EQUITY_BAR_ROW" "$out"
grep -q "VERDICT=EQUITY_NO_BARS_DIAGNOSTIC_READY" "$out"

echo "VERDICT=EQUITY_NO_BARS_DIAGNOSTIC_TEST_OK"
echo "TEST_EQUITY_NO_BARS_DIAGNOSTIC_V2_OK"
