#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile src/scripts/market_bars_health_report.py

python src/scripts/market_bars_health_report.py --help | grep -q -- "--symbols"
python src/scripts/market_bars_health_report.py --help | grep -q -- "--timeframes"

echo "MARKET_BARS_HEALTH_REPORT_COMPILE_OK"
