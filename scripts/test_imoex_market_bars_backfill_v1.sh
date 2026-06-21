#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_IMOEX_MARKET_BARS_BACKFILL_V1 ==="

out="$(mktemp)"

python3 -m py_compile src/scripts/research/build_imoex_market_bars_backfill_v1.py

PYTHONPATH=src \
RUNTIME_ALLOW_TRADING=0 \
EXECUTION_ENABLED=0 \
REAL_TRADING_ENABLED=0 \
python3 src/scripts/research/build_imoex_market_bars_backfill_v1.py | tee "$out"

grep -q "TEST_IMOEX_MARKET_BARS_BACKFILL_V1_OK" "$out"
grep -q "db_update=0" "$out"
grep -q "runtime_changed=0" "$out"
grep -q "execution_changed=0" "$out"
grep -q "telegram_send=0" "$out"
grep -q "IMOEX_BARS_ROW" "$out"
grep -Eq "VERDICT=IMOEX_MARKET_BARS_(COVERAGE_READY|BACKFILL_REQUIRED)" "$out"

echo "VERDICT=IMOEX_MARKET_BARS_BACKFILL_TEST_OK"
echo "TEST_IMOEX_MARKET_BARS_BACKFILL_V1_OK"
