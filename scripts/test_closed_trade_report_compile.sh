#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile \
  src/finam_core/analytics/closed_trade_engine.py \
  src/scripts/run_closed_trade_report.py

echo "OK: closed trade report compiles"
