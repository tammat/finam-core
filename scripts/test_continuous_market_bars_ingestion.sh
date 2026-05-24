#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH="${PYTHONPATH:-src}"

python -m py_compile src/scripts/ingestion/run_continuous_market_bars_ingestion.py

grep -q "MARKET_BARS_INGESTION_CYCLE_START" src/scripts/ingestion/run_continuous_market_bars_ingestion.py
grep -q "backfill_finam_futures_market_bars.py" src/scripts/ingestion/run_continuous_market_bars_ingestion.py

echo "TEST_CONTINUOUS_MARKET_BARS_INGESTION_OK"
