#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile \
  src/finam_core/data/volatility_scanner.py \
  src/scripts/run_volatility_scan.py

bash scripts/test_volatility_scanner.sh

echo "RUN_VOLATILITY_SCAN_MOCK_OK"
