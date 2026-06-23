#!/usr/bin/env bash
set -euo pipefail
cd /opt/finam-core || exit 1

echo "=== TEST_RS_BOTTOM_CONTRACT_ROLLING_AUDIT_V1 ==="
python3 -m py_compile src/scripts/research/build_rs_bottom_contract_rolling_audit_v1.py

out=/tmp/rs_bottom_contract_rolling_audit_v1.log
python3 src/scripts/research/build_rs_bottom_contract_rolling_audit_v1.py | tee "$out"

grep -q "CONTRACT_ROWS" "$out"
grep -q "ROLLING_AUDIT_SUMMARY" "$out"
grep -q "VERDICT=RS_BOTTOM_CONTRACT_ROLLING_AUDIT_READY" "$out"

echo "TEST_RS_BOTTOM_CONTRACT_ROLLING_AUDIT_V1_OK"
