#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_EQUITY_SIGNAL_GENERATION_AFTER_WIRING_V1 ==="

python3 -m py_compile \
src/scripts/research/build_equity_signal_generation_after_wiring_v1.py

python3 \
src/scripts/research/build_equity_signal_generation_after_wiring_v1.py \
| tee /tmp/equity_signal_generation_after_wiring_v1.log

grep -q "SUMMARY" \
/tmp/equity_signal_generation_after_wiring_v1.log

grep -q "VERDICT=" \
/tmp/equity_signal_generation_after_wiring_v1.log

echo "TEST_EQUITY_SIGNAL_GENERATION_AFTER_WIRING_V1_OK"
