#!/usr/bin/env bash
set -euo pipefail

cd "$(git rev-parse --show-toplevel)"

echo "=== TEST OPEN FORWARD UNPAIRED LOTS AUDIT V1 ==="

python3 -m py_compile src/scripts/research/build_open_forward_unpaired_lots_audit_v1.py

python3 src/scripts/research/build_open_forward_unpaired_lots_audit_v1.py \
  | tee /tmp/open_forward_unpaired_lots_audit_v1.log

grep -q "OPEN_FORWARD_UNPAIRED_LOTS_AUDIT_V1_OK" /tmp/open_forward_unpaired_lots_audit_v1.log
grep -q "TARGET_SUMMARY" /tmp/open_forward_unpaired_lots_audit_v1.log
grep -q "UNPAIRED_TOTALS" /tmp/open_forward_unpaired_lots_audit_v1.log
grep -q "VERDICT=" /tmp/open_forward_unpaired_lots_audit_v1.log
grep -q "runtime_allow=0" /tmp/open_forward_unpaired_lots_audit_v1.log
grep -q "execution_enabled=0" /tmp/open_forward_unpaired_lots_audit_v1.log

echo TEST_OPEN_FORWARD_UNPAIRED_LOTS_AUDIT_V1_OK
