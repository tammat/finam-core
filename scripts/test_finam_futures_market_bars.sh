#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH="${PYTHONPATH:-src}"

python -m py_compile \
  src/scripts/ingestion/backfill_finam_futures_market_bars.py \
  src/finam_core/ingestion/bars_client.py

grep -q "FinamBarsClient" src/scripts/ingestion/backfill_finam_futures_market_bars.py
grep -q "finam_grpc_bars_v1" src/scripts/ingestion/backfill_finam_futures_market_bars.py
grep -q "FINAM_FUTURES_MARKET_BARS_SUMMARY" src/scripts/ingestion/backfill_finam_futures_market_bars.py

echo "TEST_FINAM_FUTURES_MARKET_BARS_OK"
