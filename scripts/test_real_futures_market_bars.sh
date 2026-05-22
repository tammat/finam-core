#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH="${PYTHONPATH:-src}"

python -m py_compile \
  src/finam_core/data/finam_futures_candles_provider.py \
  src/scripts/backfill_real_futures_market_bars.py

grep -q "REAL_FUTURES_MARKET_BARS_SUMMARY" \
  src/scripts/backfill_real_futures_market_bars.py

grep -q "iss.moex.com" \
  src/finam_core/data/finam_futures_candles_provider.py

echo "TEST_REAL_FUTURES_MARKET_BARS_OK"
