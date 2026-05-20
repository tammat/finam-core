#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile src/scripts/run_real_portfolio_price_sync.py

grep -q "load_moex_last_price" src/scripts/run_real_portfolio_price_sync.py
grep -q "REAL_PORTFOLIO_PRICE_SYNC_UPDATE" src/scripts/run_real_portfolio_price_sync.py
grep -q "market_value = qty" src/scripts/run_real_portfolio_price_sync.py

echo "OK: real portfolio price sync"
