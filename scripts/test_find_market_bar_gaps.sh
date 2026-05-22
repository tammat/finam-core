#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH="${PYTHONPATH:-src}"

python -m py_compile src/scripts/find_market_bar_gaps.py

grep -q "market_bar_gaps" src/scripts/find_market_bar_gaps.py
grep -q "MARKET_BAR_GAPS_OK" src/scripts/find_market_bar_gaps.py
grep -q "missing_bars_estimate" src/scripts/find_market_bar_gaps.py

echo "TEST_FIND_MARKET_BAR_GAPS_OK"
