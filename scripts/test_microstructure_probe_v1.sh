#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core

PY_BIN="${PY_BIN:-/opt/finam-core/venv/bin/python}"

if [[ ! -x "$PY_BIN" ]]; then
  PY_BIN="$(command -v python3)"
fi

echo "TEST_MICROSTRUCTURE_PROBE_V1_START"

"$PY_BIN" -m py_compile \
  src/scripts/research/build_microstructure_probe_v1.py

"$PY_BIN" src/scripts/research/build_microstructure_probe_v1.py \
  > /tmp/microstructure_probe_v1.out

grep -q "=== MICROSTRUCTURE_PROBE_V1 ===" /tmp/microstructure_probe_v1.out
grep -q "microstructure_score=" /tmp/microstructure_probe_v1.out
grep -q "verdict=" /tmp/microstructure_probe_v1.out

echo "TEST_MICROSTRUCTURE_PROBE_V1_OK"
