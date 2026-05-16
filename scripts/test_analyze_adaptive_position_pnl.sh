#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile \
  src/scripts/analyze_adaptive_position_pnl.py

PYTHONPATH=src python \
  src/scripts/analyze_adaptive_position_pnl.py

test -f reports/adaptive_position_pnl.tsv

grep -q "multiplier" reports/adaptive_position_pnl.tsv
grep -q "trades" reports/adaptive_position_pnl.tsv
grep -q "total_notional" reports/adaptive_position_pnl.tsv

echo "OK: adaptive position pnl analytics"
