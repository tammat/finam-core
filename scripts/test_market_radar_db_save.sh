#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile src/scripts/run_market_radar.py

PYTHONPATH=src python -m scripts.run_market_radar \
  --top-n 3 \
  --min-value 50000000 \
  --no-db | grep -q "MARKET_RADAR_DB_SAVE_SKIPPED"

echo "MARKET_RADAR_DB_SAVE_TEST_OK"
