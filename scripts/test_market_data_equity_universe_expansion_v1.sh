#!/usr/bin/env bash
set -euo pipefail

ROOT="$(git rev-parse --show-toplevel)"
cd "$ROOT"

python3 -m py_compile src/scripts/ingestion/backfill_equity_watch_market_bars_v1.py

grep -q "GAZP@MISX" src/scripts/ingestion/backfill_equity_watch_market_bars_v1.py
grep -q "PLZL@MISX" src/scripts/ingestion/backfill_equity_watch_market_bars_v1.py
grep -q "SBER@MISX" src/scripts/ingestion/backfill_equity_watch_market_bars_v1.py
grep -q "LKOH@MISX" src/scripts/ingestion/backfill_equity_watch_market_bars_v1.py
grep -q "LOOKBACK_HOURS = 24" src/scripts/ingestion/backfill_equity_watch_market_bars_v1.py

python3 src/scripts/ingestion/backfill_equity_watch_market_bars_v1.py

echo TEST_MARKET_DATA_EQUITY_UNIVERSE_EXPANSION_V1_OK
