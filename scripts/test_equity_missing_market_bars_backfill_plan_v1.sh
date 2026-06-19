#!/usr/bin/env bash
set -euo pipefail

cd "$(git rev-parse --show-toplevel)"

echo "=== TEST EQUITY MISSING MARKET BARS BACKFILL PLAN V1 ==="
echo "runtime_allow=0"
echo "execution_enabled=0"
echo "real_trading_enabled=0"
echo "orders_create=0"
echo "execution_intents_create=0"

python3 -m py_compile src/scripts/research/build_equity_missing_market_bars_backfill_plan_v1.py

PYTHONPATH=src \
RUNTIME_ALLOW_TRADING=0 EXECUTION_ENABLED=0 REAL_TRADING_ENABLED=0 \
python3 src/scripts/research/build_equity_missing_market_bars_backfill_plan_v1.py \
  | tee /tmp/equity_missing_market_bars_backfill_plan_v1.log

grep -q "EQUITY_MISSING_MARKET_BARS_BACKFILL_PLAN_V1_OK" /tmp/equity_missing_market_bars_backfill_plan_v1.log
grep -q "symbol=OZON@MISX" /tmp/equity_missing_market_bars_backfill_plan_v1.log
grep -q "symbol=SBERP@MISX" /tmp/equity_missing_market_bars_backfill_plan_v1.log
grep -q "symbol=T@MISX" /tmp/equity_missing_market_bars_backfill_plan_v1.log
grep -q "missing_market_bars=" /tmp/equity_missing_market_bars_backfill_plan_v1.log
grep -q "BACKFILL_SCRIPT_CANDIDATES" /tmp/equity_missing_market_bars_backfill_plan_v1.log
grep -q "orders_create=0" /tmp/equity_missing_market_bars_backfill_plan_v1.log
grep -q "execution_intents_create=0" /tmp/equity_missing_market_bars_backfill_plan_v1.log
grep -q "execution_enabled=0" /tmp/equity_missing_market_bars_backfill_plan_v1.log
grep -q "real_trading_enabled=0" /tmp/equity_missing_market_bars_backfill_plan_v1.log
grep -q "VERDICT=" /tmp/equity_missing_market_bars_backfill_plan_v1.log

echo "=== EQUITY BACKFILL PLAN SUMMARY ==="
grep -E "EQUITY_BACKFILL_TARGET_ROW|BACKFILL_SCRIPT_ROW|missing_market_bars=|candidate_scripts=|VERDICT=" \
  /tmp/equity_missing_market_bars_backfill_plan_v1.log | head -100

echo TEST_EQUITY_MISSING_MARKET_BARS_BACKFILL_PLAN_V1_OK
