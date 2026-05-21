#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile \
  src/finam_core/data/market_bars_source.py \
  src/scripts/run_market_bars_source_backfill.py

grep -q "create table if not exists market_bars" \
  src/finam_core/data/market_bars_source.py

grep -q "load_closes" \
  src/finam_core/data/market_bars_source.py

echo "OK: market bars source"
