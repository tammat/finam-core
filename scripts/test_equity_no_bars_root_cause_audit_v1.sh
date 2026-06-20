#!/usr/bin/env bash
set -euo pipefail

echo "=== EQUITY_NO_BARS_ROOT_CAUSE_AUDIT_V1 ==="

out="$(mktemp)"

python3 -m py_compile \
  src/scripts/research/build_equity_no_bars_root_cause_audit_v1.py

python3 src/scripts/research/build_equity_no_bars_root_cause_audit_v1.py | tee "$out"

grep -q "VERDICT=EQUITY_NO_BARS_ROOT_CAUSE_AUDIT_READY" "$out"
grep -q "TEST_EQUITY_NO_BARS_ROOT_CAUSE_AUDIT_V1_OK" "$out"

echo "VERDICT=EQUITY_NO_BARS_ROOT_CAUSE_AUDIT_TEST_OK"
