#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core

PY_BIN="${PY_BIN:-/opt/finam-core/venv/bin/python}"
if [[ ! -x "$PY_BIN" ]]; then
  PY_BIN="$(command -v python3)"
fi

echo "TEST_NG_SIGNAL_ID_PROPAGATION_V1_START"

"$PY_BIN" -m py_compile src/finam_core/pipelines/paper_pipeline.py

grep -q "NG_SIGNAL_ID_PROPAGATION_V1" src/finam_core/pipelines/paper_pipeline.py
grep -q "_propagate_signal_id_to_fill_v1" src/finam_core/pipelines/paper_pipeline.py

echo "TEST_NG_SIGNAL_ID_PROPAGATION_V1_OK"
