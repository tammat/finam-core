#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core

PY_BIN="${PY_BIN:-/opt/finam-core/venv/bin/python}"

if [[ ! -x "$PY_BIN" ]]; then
  PY_BIN="$(command -v python3)"
fi

echo "TEST_LKOH_EDGE_BIAS_AUDIT_V1_START"

"$PY_BIN" -m py_compile \
  src/scripts/observability/build_lkoh_edge_bias_audit_v1.py

"$PY_BIN" src/scripts/observability/build_lkoh_edge_bias_audit_v1.py \
  > /tmp/lkoh_edge_bias_audit_v1.out

grep -q "=== LKOH EDGE BIAS AUDIT V1 ===" /tmp/lkoh_edge_bias_audit_v1.out
grep -q "=== BIAS VERDICT ===" /tmp/lkoh_edge_bias_audit_v1.out
grep -q "status=" /tmp/lkoh_edge_bias_audit_v1.out

echo "TEST_LKOH_EDGE_BIAS_AUDIT_V1_OK"
