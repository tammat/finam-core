#!/usr/bin/env bash
set -euo pipefail

cd "$(git rev-parse --show-toplevel)"
export PYTHONPATH=src

python3 -m py_compile \
  src/scripts/architecture/build_source_separation_audit_v1.py

python3 \
  src/scripts/architecture/build_source_separation_audit_v1.py \
  | tee /tmp/source_separation_audit_v1.log

grep -q "SOURCE SEPARATION AUDIT V1" \
  /tmp/source_separation_audit_v1.log

grep -q "SOURCE_LAYER=TRADES" \
  /tmp/source_separation_audit_v1.log

grep -q "SOURCE_LAYER=CLOSED_TRADE_CHAINS_V3" \
  /tmp/source_separation_audit_v1.log

grep -q "SOURCE_LAYER=TRADE_ATTRIBUTION_V3" \
  /tmp/source_separation_audit_v1.log

grep -q "SOURCE_SEPARATION_AUDIT_V1_OK" \
  /tmp/source_separation_audit_v1.log

echo TEST_SOURCE_SEPARATION_AUDIT_V1_OK
