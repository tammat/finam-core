#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_RS_BOTTOM_FORWARD_VALIDATION_V1 ==="

out="$(mktemp)"

python3 -m py_compile src/scripts/research/build_rs_bottom_forward_validation_v1.py

PYTHONPATH=src \
RUNTIME_ALLOW_TRADING=0 \
EXECUTION_ENABLED=0 \
REAL_TRADING_ENABLED=0 \
python3 src/scripts/research/build_rs_bottom_forward_validation_v1.py | tee "$out"

grep -q "TEST_RS_BOTTOM_FORWARD_VALIDATION_V1_OK" "$out"
grep -q "db_update=0" "$out"
grep -q "runtime_changed=0" "$out"
grep -q "execution_changed=0" "$out"
grep -q "telegram_send=0" "$out"
grep -q "RS_BOTTOM_FORWARD_VALIDATION_ROW" "$out"
grep -Eq "VERDICT=RS_BOTTOM_FORWARD_VALIDATION_(COLLECTING|DECISION_READY)" "$out"

echo "VERDICT=RS_BOTTOM_FORWARD_VALIDATION_TEST_OK"
echo "TEST_RS_BOTTOM_FORWARD_VALIDATION_V1_OK"
