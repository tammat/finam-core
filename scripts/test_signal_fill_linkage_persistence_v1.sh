#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core

PY_BIN="${PY_BIN:-/opt/finam-core/venv/bin/python}"
if [[ ! -x "$PY_BIN" ]]; then
  PY_BIN="$(command -v python3)"
fi

echo "TEST_SIGNAL_FILL_LINKAGE_PERSISTENCE_V1_START"

"$PY_BIN" -m py_compile src/finam_core/execution/fill_persistence_service.py

grep -q "SIGNAL_FILL_LINKAGE_PERSISTENCE_V1" src/finam_core/execution/fill_persistence_service.py
grep -q "_persist_signal_fill_linkage_v1" src/finam_core/execution/fill_persistence_service.py
grep -q "INSERT INTO signal_fills" src/finam_core/execution/fill_persistence_service.py

echo "TEST_SIGNAL_FILL_LINKAGE_PERSISTENCE_V1_OK"
