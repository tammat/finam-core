#!/usr/bin/env bash
set -euo pipefail

cd "$(git rev-parse --show-toplevel)"
export PYTHONPATH=src

python3 -m py_compile \
  src/scripts/research/build_chain_provenance_audit_v1.py

python3 \
  src/scripts/research/build_chain_provenance_audit_v1.py \
  | tee /tmp/chain_provenance_audit_v1.log

grep -q "CHAIN PROVENANCE AUDIT V1" \
  /tmp/chain_provenance_audit_v1.log

grep -q "CHAIN_PROVENANCE_AUDIT_SUMMARY" \
  /tmp/chain_provenance_audit_v1.log

grep -q "CHAIN_PROVENANCE_AUDIT_V1_OK" \
  /tmp/chain_provenance_audit_v1.log

echo TEST_CHAIN_PROVENANCE_AUDIT_V1_OK
