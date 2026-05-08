#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile src/scripts/run_market_radar.py

python -m scripts.run_market_radar --help | grep -q -- "--telegram-top5"

echo "MARKET_RADAR_TELEGRAM_FLAG_OK"
