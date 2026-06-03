#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core

PY_BIN="${PY_BIN:-/opt/finam-core/venv/bin/python}"
if [[ ! -x "$PY_BIN" ]]; then
  PY_BIN="$(command -v python3)"
fi

echo "TEST_POSITION_PROJECTION_ON_FILL_V1_START"

"$PY_BIN" -m py_compile src/finam_core/pipelines/paper_pipeline.py

grep -q "POSITION_PROJECTION_ON_FILL_V1" src/finam_core/pipelines/paper_pipeline.py
grep -q "_update_position_projection_on_fill_v1" src/finam_core/pipelines/paper_pipeline.py
grep -q "PIPE_POSITION_PROJECTION_UPDATED" src/finam_core/pipelines/paper_pipeline.py

echo "TEST_POSITION_PROJECTION_ON_FILL_V1_OK"
