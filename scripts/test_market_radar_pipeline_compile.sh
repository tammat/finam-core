#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile \
  src/scripts/run_market_radar.py \
  src/finam_core/data/moex_client.py \
  src/finam_core/data/market_radar.py \
  src/finam_core/storage/dynamic_watchlist_repository.py

PYTHONPATH=src python -m scripts.run_market_radar \
  --top-n 3 \
  --min-value 50000000 \
  --no-db | grep -q "MARKET_RADAR_CLEAN_OK"

echo "MARKET_RADAR_PIPELINE_COMPILE_OK"
