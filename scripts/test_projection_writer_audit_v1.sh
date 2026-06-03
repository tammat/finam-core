#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core

PY_BIN="${PY_BIN:-/opt/finam-core/venv/bin/python}"
if [[ ! -x "$PY_BIN" ]]; then
  PY_BIN="$(command -v python3)"
fi

echo "TEST_PROJECTION_WRITER_AUDIT_V1_START"

"$PY_BIN" -m py_compile src/scripts/observability/build_projection_writer_audit_v1.py

"$PY_BIN" src/scripts/observability/build_projection_writer_audit_v1.py > /tmp/projection_writer_audit_v1.out

grep -q "PROJECTION WRITER AUDIT V1" /tmp/projection_writer_audit_v1.out
grep -q "SUMMARY" /tmp/projection_writer_audit_v1.out
grep -q "verdict=" /tmp/projection_writer_audit_v1.out

echo "TEST_PROJECTION_WRITER_AUDIT_V1_OK"
