#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile \
  src/scripts/research/build_br_trade_duration_decomposition_v1.py

grep -q "SCALP_LT_5M" \
  src/scripts/research/build_br_trade_duration_decomposition_v1.py

grep -q "FAST_5_15M" \
  src/scripts/research/build_br_trade_duration_decomposition_v1.py

grep -q "INTRADAY_15_60M" \
  src/scripts/research/build_br_trade_duration_decomposition_v1.py

grep -q "SWING_1_4H" \
  src/scripts/research/build_br_trade_duration_decomposition_v1.py

grep -q "BR_TRADE_DURATION_DECOMPOSITION_V1_OK" \
  src/scripts/research/build_br_trade_duration_decomposition_v1.py

echo "BR_TRADE_DURATION_DECOMPOSITION_V1_TEST_OK"
