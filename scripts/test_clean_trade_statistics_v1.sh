#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile \
  src/scripts/analytics/build_clean_trade_statistics_v1.py

python \
  src/scripts/analytics/build_clean_trade_statistics_v1.py

echo CLEAN_TRADE_STATISTICS_V1_OK
