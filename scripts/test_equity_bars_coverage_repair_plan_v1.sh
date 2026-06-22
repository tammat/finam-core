#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_EQUITY_BARS_COVERAGE_REPAIR_PLAN_V1 ==="

out="$(mktemp)"

python3 -m py_compile src/scripts/research/build_equity_bars_coverage_repair_plan_v1.py

PYTHONPATH=src \
RUNTIME_ALLOW_TRADING=0 \
EXECUTION_ENABLED=0 \
REAL_TRADING_ENABLED=0 \
python3 src/scripts/research/build_equity_bars_coverage_repair_plan_v1.py | tee "$out"

grep -q "TEST_EQUITY_BARS_COVERAGE_REPAIR_PLAN_V1_OK" "$out"
grep -q "db_update=0" "$out"
grep -q "runtime_changed=0" "$out"
grep -q "execution_changed=0" "$out"
grep -q "telegram_send=0" "$out"
grep -q "EQUITY_BARS_REPAIR_ROW" "$out"
grep -Eq "VERDICT=EQUITY_BARS_COVERAGE_(REPAIR_PLAN_REQUIRED|OK)" "$out"

echo "VERDICT=EQUITY_BARS_COVERAGE_REPAIR_PLAN_TEST_OK"
echo "TEST_EQUITY_BARS_COVERAGE_REPAIR_PLAN_V1_OK"
