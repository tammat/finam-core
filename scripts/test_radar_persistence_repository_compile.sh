#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile \
  src/finam_core/data/radar_persistence_engine.py \
  src/finam_core/data/radar_persistence_repository.py \
  src/finam_core/storage/dynamic_watchlist_repository.py \
  src/scripts/run_market_radar.py

echo "RADAR_PERSISTENCE_SQL_COMPILE_OK"
