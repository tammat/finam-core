#!/usr/bin/env bash
set -euo pipefail

cd "$(git rev-parse --show-toplevel)"

echo "=== TEST NGQ6 FORWARD ACCUMULATION VERIFY V3 ==="

python3 -m py_compile src/scripts/research/build_ngq6_forward_accumulation_verify_v3.py

python3 src/scripts/research/build_ngq6_forward_accumulation_verify_v3.py \
  | tee /tmp/ngq6_forward_accumulation_verify_v3.log

grep -q "NGQ6_FORWARD_ACCUMULATION_VERIFY_V3_OK" /tmp/ngq6_forward_accumulation_verify_v3.log
grep -q "VERDICT=" /tmp/ngq6_forward_accumulation_verify_v3.log
grep -q "runtime_allow=0" /tmp/ngq6_forward_accumulation_verify_v3.log
grep -q "execution_enabled=0" /tmp/ngq6_forward_accumulation_verify_v3.log

echo TEST_NGQ6_FORWARD_ACCUMULATION_VERIFY_V3_OK
