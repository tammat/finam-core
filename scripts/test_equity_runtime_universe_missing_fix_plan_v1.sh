#!/usr/bin/env bash
set -euo pipefail

echo "=== EQUITY_RUNTIME_UNIVERSE_MISSING_FIX_PLAN_V1 ==="

out="$(mktemp)"

python3 -m py_compile src/scripts/research/build_equity_runtime_universe_missing_fix_plan_v1.py
python3 src/scripts/research/build_equity_runtime_universe_missing_fix_plan_v1.py | tee "$out"

grep -q "VERDICT=EQUITY_RUNTIME_UNIVERSE_MISSING_FIX_PLAN_READY" "$out"
grep -q "TEST_EQUITY_RUNTIME_UNIVERSE_MISSING_FIX_PLAN_V1_OK" "$out"
grep -q '"db_update": 0' "$out"
grep -q '"runtime_changed": 0' "$out"
grep -q '"execution_changed": 0' "$out"
grep -q 'EUTR@MISX' "$out"

echo "VERDICT=EQUITY_RUNTIME_UNIVERSE_MISSING_FIX_PLAN_TEST_OK"
echo "TEST_EQUITY_RUNTIME_UNIVERSE_MISSING_FIX_PLAN_V1_OK"
