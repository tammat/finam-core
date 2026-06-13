#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core

PY_BIN="${PY_BIN:-/opt/finam-core/venv/bin/python}"

if [[ ! -x "$PY_BIN" ]]; then
  PY_BIN="$(command -v python3)"
fi

echo "TEST_FINAM_API_CAPABILITY_AUDIT_V1_START"

"$PY_BIN" -m py_compile \
  src/scripts/research/build_finam_api_capability_audit_v1.py

"$PY_BIN" src/scripts/research/build_finam_api_capability_audit_v1.py \
  > /tmp/finam_api_capability_audit_v1.out

grep -q "=== FINAM API CAPABILITY AUDIT V1 ===" /tmp/finam_api_capability_audit_v1.out
grep -q "ORDER_BOOK=" /tmp/finam_api_capability_audit_v1.out
grep -q "BEST_BID_ASK=" /tmp/finam_api_capability_audit_v1.out
grep -q "verdict=" /tmp/finam_api_capability_audit_v1.out

echo "TEST_FINAM_API_CAPABILITY_AUDIT_V1_OK"
