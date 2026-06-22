#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_EQUITY_BARS_BACKFILL_APPLY_PLAN_V1 ==="

out="$(mktemp)"

python3 -m py_compile src/scripts/research/build_equity_bars_backfill_apply_plan_v1.py

PYTHONPATH=src \
RUNTIME_ALLOW_TRADING=0 \
EXECUTION_ENABLED=0 \
REAL_TRADING_ENABLED=0 \
python3 src/scripts/research/build_equity_bars_backfill_apply_plan_v1.py | tee "$out"

grep -q "TEST_EQUITY_BARS_BACKFILL_APPLY_PLAN_V1_OK" "$out"
grep -q "db_update=0" "$out"
grep -q "runtime_changed=0" "$out"
grep -q "execution_changed=0" "$out"
grep -q "telegram_send=0" "$out"
grep -q "planned_actions=" "$out"
grep -Eq "VERDICT=EQUITY_BARS_BACKFILL_APPLY_PLAN_(REQUIRED|NO_ACTION)" "$out"

if grep -q "VERDICT=EQUITY_BARS_BACKFILL_APPLY_PLAN_REQUIRED" "$out"; then
  grep -q "EQUITY_BACKFILL_PLAN_ROW" "$out"
  grep -q "EQUITY_BACKFILL_COMMAND" "$out"
fi

echo "VERDICT=EQUITY_BARS_BACKFILL_APPLY_PLAN_TEST_OK"
echo "TEST_EQUITY_BARS_BACKFILL_APPLY_PLAN_V1_OK"
