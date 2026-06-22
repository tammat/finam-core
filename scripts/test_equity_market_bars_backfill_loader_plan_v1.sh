#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_EQUITY_MARKET_BARS_BACKFILL_LOADER_PLAN_V1 ==="

out="$(mktemp)"

python3 -m py_compile src/scripts/research/build_equity_market_bars_backfill_loader_plan_v1.py

PYTHONPATH=src \
RUNTIME_ALLOW_TRADING=0 \
EXECUTION_ENABLED=0 \
REAL_TRADING_ENABLED=0 \
python3 src/scripts/research/build_equity_market_bars_backfill_loader_plan_v1.py | tee "$out"

grep -q "TEST_EQUITY_MARKET_BARS_BACKFILL_LOADER_PLAN_V1_OK" "$out"
grep -q "db_update=0" "$out"
grep -q "runtime_changed=0" "$out"
grep -q "execution_changed=0" "$out"
grep -q "telegram_send=0" "$out"
grep -q "PROPOSED_LOADER" "$out"
grep -q "TARGET_SYMBOL_ROW" "$out"
grep -q "VERDICT=EQUITY_MARKET_BARS_BACKFILL_LOADER_PLAN_READY" "$out"

echo "VERDICT=EQUITY_MARKET_BARS_BACKFILL_LOADER_PLAN_TEST_OK"
echo "TEST_EQUITY_MARKET_BARS_BACKFILL_LOADER_PLAN_V1_OK"
