#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core

PY_BIN="${PY_BIN:-/opt/finam-core/venv/bin/python}"
[[ -x "$PY_BIN" ]] || PY_BIN="$(command -v python3)"

echo "TEST_PLZL_BATCH_AUDIT_V1_START"

"$PY_BIN" -m py_compile src/scripts/analytics/build_plzl_batch_audit_v1.py

SYMBOL=PLZL@MISX "$PY_BIN" src/scripts/analytics/build_plzl_batch_audit_v1.py \
  > /tmp/plzl_batch_audit_v1.out

grep -q "PLZL BATCH AUDIT V1" /tmp/plzl_batch_audit_v1.out
grep -q "SUMMARY" /tmp/plzl_batch_audit_v1.out
grep -q "PNL" /tmp/plzl_batch_audit_v1.out
grep -q "TOP_BATCHES" /tmp/plzl_batch_audit_v1.out
grep -q "VERDICT" /tmp/plzl_batch_audit_v1.out

echo "TEST_PLZL_BATCH_AUDIT_V1_OK"
