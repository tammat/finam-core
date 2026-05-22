#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH="${PYTHONPATH:-src}"

python -m py_compile src/scripts/backfill_futures_market_bars.py

grep -q "FUTURES_MARKET_BARS_BACKFILL_SUMMARY" src/scripts/backfill_futures_market_bars.py
grep -q "synthetic_futures_backfill_v1" src/scripts/backfill_futures_market_bars.py
grep -q "market_bars" src/scripts/backfill_futures_market_bars.py

echo "TEST_FUTURES_MARKET_BARS_BACKFILL_OK"
