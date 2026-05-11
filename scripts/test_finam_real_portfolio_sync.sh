#!/usr/bin/env bash
set -euo pipefail

test -f src/finam_core/portfolio/finam_real_portfolio_sync.py
test -x scripts/sync_real_portfolio_from_finam.sh

grep -q "FinamTokenManager" src/finam_core/portfolio/finam_real_portfolio_sync.py
grep -q "https://api.finam.ru/v1/accounts" src/finam_core/portfolio/finam_real_portfolio_sync.py
grep -q "real_portfolio_positions" src/finam_core/portfolio/finam_real_portfolio_sync.py
grep -q "FINAM_REAL_PORTFOLIO_SYNC_OK" src/finam_core/portfolio/finam_real_portfolio_sync.py

echo "FINAM_REAL_PORTFOLIO_SYNC_SCRIPT_OK"
