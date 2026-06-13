#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core

PY_BIN="${PY_BIN:-/opt/finam-core/venv/bin/python}"

if [[ ! -x "$PY_BIN" ]]; then
  PY_BIN="$(command -v python3)"
fi

echo "TEST_NG_SIGNAL_LINKAGE_V1_START"

"$PY_BIN" -m py_compile src/finam_core/pipelines/paper_pipeline.py

grep -q "NG_SIGNAL_LINKAGE_V1" src/finam_core/pipelines/paper_pipeline.py
grep -q "linked_signal_id" src/finam_core/pipelines/paper_pipeline.py
grep -q "strategy_signal" src/finam_core/pipelines/paper_pipeline.py

echo "TEST_NG_SIGNAL_LINKAGE_V1_OK"
