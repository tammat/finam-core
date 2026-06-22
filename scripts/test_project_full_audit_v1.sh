#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_PROJECT_FULL_AUDIT_V1 ==="

out="$(mktemp)"

python3 -m py_compile src/scripts/research/build_project_full_audit_v1.py

PYTHONPATH=src \
RUNTIME_ALLOW_TRADING=0 \
EXECUTION_ENABLED=0 \
REAL_TRADING_ENABLED=0 \
python3 src/scripts/research/build_project_full_audit_v1.py | tee "$out"

grep -q "TEST_PROJECT_FULL_AUDIT_V1_OK" "$out"
grep -q "db_update=0" "$out"
grep -q "runtime_changed=0" "$out"
grep -q "execution_changed=0" "$out"
grep -q "telegram_send=0" "$out"
grep -q "RS_BOTTOM_FORWARD_STATE" "$out"
grep -q "VERDICT=PROJECT_FULL_AUDIT_READY" "$out"

echo "VERDICT=PROJECT_FULL_AUDIT_TEST_OK"
echo "TEST_PROJECT_FULL_AUDIT_V1_OK"
