#!/usr/bin/env bash
set -euo pipefail

echo "=== EQUITY_MARKET_BARS_BACKFILL_AND_WIRING_FIX_V1 ==="

out="$(mktemp)"

python3 -m py_compile \
  src/scripts/research/build_equity_market_bars_backfill_and_wiring_fix_v1.py

python3 src/scripts/research/build_equity_market_bars_backfill_and_wiring_fix_v1.py | tee "$out"

grep -q "VERDICT=EQUITY_MARKET_BARS_BACKFILL_AND_WIRING_FIX_PLAN_READY" "$out"
grep -q "TEST_EQUITY_MARKET_BARS_BACKFILL_AND_WIRING_FIX_V1_OK" "$out"
grep -q '"db_update": 0' "$out"
grep -q '"runtime_changed": 0' "$out"
grep -q '"execution_changed": 0' "$out"

echo "VERDICT=EQUITY_MARKET_BARS_BACKFILL_AND_WIRING_FIX_TEST_OK"
echo "TEST_EQUITY_MARKET_BARS_BACKFILL_AND_WIRING_FIX_V1_OK"
