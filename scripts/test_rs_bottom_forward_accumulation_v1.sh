#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_RS_BOTTOM_FORWARD_ACCUMULATION_V1 ==="

out="$(mktemp)"

PYTHONPATH=src \
RUNTIME_ALLOW_TRADING=0 \
EXECUTION_ENABLED=0 \
REAL_TRADING_ENABLED=0 \
python3 src/scripts/research/build_rs_bottom_forward_accumulation_v1.py | tee "$out"

grep -q "TEST_RS_BOTTOM_FORWARD_ACCUMULATION_V1_OK" "$out"
grep -q "completed_total=" "$out"
grep -Eq "VERDICT=(FORWARD_ACCUMULATION|FORWARD_EARLY_REVIEW|FORWARD_DECISION_READY)" "$out"

echo "VERDICT=RS_BOTTOM_FORWARD_ACCUMULATION_TEST_OK"
echo "TEST_RS_BOTTOM_FORWARD_ACCUMULATION_V1_OK"
