#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH="${PYTHONPATH:-src}"

python -m py_compile src/scripts/ingestion/backfill_finam_futures_market_bars.py

python src/scripts/ingestion/backfill_finam_futures_market_bars.py --help | grep -q -- "--symbols"

echo "TEST_BACKFILL_FINAM_FUTURES_SYMBOLS_ARG_OK"
