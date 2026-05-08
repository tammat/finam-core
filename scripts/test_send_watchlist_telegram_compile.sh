#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile src/scripts/send_watchlist_telegram.py

echo "SEND_WATCHLIST_TELEGRAM_COMPILE_OK"
