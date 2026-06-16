#!/usr/bin/env bash
set -euo pipefail

cd "$(git rev-parse --show-toplevel)"
export PYTHONPATH=src

python3 -m py_compile \
  src/scripts/research/build_fill_chain_pairing_audit_v1.py

python3 \
  src/scripts/research/build_fill_chain_pairing_audit_v1.py \
  | tee /tmp/fill_chain_pairing_audit_v1.log

grep -q "FILL CHAIN PAIRING AUDIT V1" \
  /tmp/fill_chain_pairing_audit_v1.log

grep -q "FILL_CHAIN_PAIRING_AUDIT_SUMMARY" \
  /tmp/fill_chain_pairing_audit_v1.log

grep -q "FILL_CHAIN_PAIRING_AUDIT_V1_OK" \
  /tmp/fill_chain_pairing_audit_v1.log

echo TEST_FILL_CHAIN_PAIRING_AUDIT_V1_OK
