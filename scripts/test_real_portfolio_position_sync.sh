#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile src/scripts/run_real_portfolio_position_sync.py

grep -q "REAL_PORTFOLIO_POSITION_SYNC_OK" src/scripts/run_real_portfolio_position_sync.py
grep -q "real_portfolio_positions" src/scripts/run_real_portfolio_position_sync.py
grep -q "REAL_POSITION_SYNC_SYMBOL" src/scripts/run_real_portfolio_position_sync.py
grep -q "client_has_no_position_method" src/scripts/run_real_portfolio_position_sync.py

echo "OK: real portfolio position sync"
