#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_FUTURES_RS_BOTTOM_SIGN_CONSISTENCY_AUDIT_V1 ==="

out="$(mktemp)"

python3 -m py_compile src/scripts/research/build_futures_rs_bottom_sign_consistency_audit_v1.py

PYTHONPATH=src \
RUNTIME_ALLOW_TRADING=0 \
EXECUTION_ENABLED=0 \
REAL_TRADING_ENABLED=0 \
python3 src/scripts/research/build_futures_rs_bottom_sign_consistency_audit_v1.py | tee "$out"

grep -q "TEST_FUTURES_RS_BOTTOM_SIGN_CONSISTENCY_AUDIT_V1_OK" "$out"
grep -q "db_update=0" "$out"
grep -q "runtime_changed=0" "$out"
grep -q "execution_changed=0" "$out"
grep -q "telegram_send=0" "$out"
grep -q "SIGN_AUDIT_ROW" "$out"
grep -Eq "VERDICT=(SIGN_BUG_CONFIRMED|SIGN_CONSISTENCY_OK|SELECTION_MISMATCH)" "$out"

echo "VERDICT=FUTURES_RS_BOTTOM_SIGN_CONSISTENCY_AUDIT_TEST_OK"
echo "TEST_FUTURES_RS_BOTTOM_SIGN_CONSISTENCY_AUDIT_V1_OK"
