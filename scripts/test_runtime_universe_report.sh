#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile \
  src/scripts/generate_runtime_universe_report.py

PYTHONPATH=src python \
  src/scripts/generate_runtime_universe_report.py

test -f reports/runtime_universe_state.tsv

grep -q "symbol" reports/runtime_universe_state.tsv
grep -q "strategy" reports/runtime_universe_state.tsv
grep -q "regime" reports/runtime_universe_state.tsv
grep -q "eviction_blocked_by_position" reports/runtime_universe_state.tsv

echo "OK: runtime universe state report"
