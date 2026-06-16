#!/usr/bin/env bash
set -euo pipefail

cd "$(git rev-parse --show-toplevel)"
export PYTHONPATH=src

python3 -m py_compile src/scripts/research/build_gold_shadow_to_paper_wiring_audit_v1.py

python3 src/scripts/research/build_gold_shadow_to_paper_wiring_audit_v1.py \
  | tee /tmp/gold_shadow_to_paper_wiring_audit_v1.log

grep -q "GOLD_SHADOW_TO_PAPER_WIRING_AUDIT_V1_OK" /tmp/gold_shadow_to_paper_wiring_audit_v1.log
grep -q "GDU6@RTSX" /tmp/gold_shadow_to_paper_wiring_audit_v1.log
grep -q "PAPER_ACCUMULATION_CANDIDATE" /tmp/gold_shadow_to_paper_wiring_audit_v1.log

if grep -q "runtime_allow=1" /tmp/gold_shadow_to_paper_wiring_audit_v1.log; then
  echo "FAIL: runtime was enabled"
  exit 1
fi

if grep -q "execution_enabled=1" /tmp/gold_shadow_to_paper_wiring_audit_v1.log; then
  echo "FAIL: execution was enabled"
  exit 1
fi

echo TEST_GOLD_SHADOW_TO_PAPER_WIRING_AUDIT_V1_OK
