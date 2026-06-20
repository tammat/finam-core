#!/usr/bin/env bash
set -euo pipefail

echo "=== EUTR_NO_BARS_ROOT_CAUSE_AUDIT_V1 ==="

out="$(mktemp)"

python3 -m py_compile src/scripts/research/build_eutr_no_bars_root_cause_audit_v1.py
python3 src/scripts/research/build_eutr_no_bars_root_cause_audit_v1.py | tee "$out"

grep -q "VERDICT=EUTR_NO_BARS_ROOT_CAUSE_AUDIT_READY" "$out"
grep -q "TEST_EUTR_NO_BARS_ROOT_CAUSE_AUDIT_V1_OK" "$out"
grep -q '"db_update": 0' "$out"
grep -q '"runtime_changed": 0' "$out"
grep -q '"execution_changed": 0' "$out"
grep -q '"symbol": "EUTR@MISX"' "$out"

echo "VERDICT=EUTR_NO_BARS_ROOT_CAUSE_AUDIT_TEST_OK"
echo "TEST_EUTR_NO_BARS_ROOT_CAUSE_AUDIT_V1_OK"
