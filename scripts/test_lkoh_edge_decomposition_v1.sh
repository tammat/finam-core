#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core

PY_BIN="${PY_BIN:-/opt/finam-core/venv/bin/python}"

if [[ ! -x "$PY_BIN" ]]; then
  PY_BIN="$(command -v python3)"
fi

echo "TEST_LKOH_EDGE_DECOMPOSITION_V1_START"

"$PY_BIN" -m py_compile \
  src/scripts/observability/build_lkoh_edge_decomposition_v1.py

"$PY_BIN" src/scripts/observability/build_lkoh_edge_decomposition_v1.py \
  > /tmp/lkoh_edge_decomposition_v1.out

grep -q "=== LKOH EDGE DECOMPOSITION V1 ===" /tmp/lkoh_edge_decomposition_v1.out
grep -q "=== ПО ЧАСАМ МСК ===" /tmp/lkoh_edge_decomposition_v1.out
grep -q "=== ПО ДНЯМ НЕДЕЛИ ===" /tmp/lkoh_edge_decomposition_v1.out

echo "TEST_LKOH_EDGE_DECOMPOSITION_V1_OK"
