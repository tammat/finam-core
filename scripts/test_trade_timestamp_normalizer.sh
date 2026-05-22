#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH="${PYTHONPATH:-src}"

python -m py_compile src/scripts/build_trade_timestamp_normalizer.py

grep -q "trade_timestamp_normalization_audit" src/scripts/build_trade_timestamp_normalizer.py
grep -q "SHIFT_PLUS" src/scripts/build_trade_timestamp_normalizer.py
grep -q "SHIFT_MINUS" src/scripts/build_trade_timestamp_normalizer.py
grep -q "TRADE_TIMESTAMP_NORMALIZER_SUMMARY" src/scripts/build_trade_timestamp_normalizer.py

echo "TEST_TRADE_TIMESTAMP_NORMALIZER_OK"
