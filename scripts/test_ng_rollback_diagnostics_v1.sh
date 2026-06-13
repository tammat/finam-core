#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core

PY_BIN="${PY_BIN:-/opt/finam-core/venv/bin/python}"

if [[ ! -x "$PY_BIN" ]]; then
  PY_BIN="$(command -v python3)"
fi

echo "TEST_NG_ROLLBACK_DIAGNOSTICS_V1_START"

"$PY_BIN" -m py_compile src/finam_core/pipelines/paper_pipeline.py

grep -q "PIPE_NG_INTENT_ROLLBACK_BLOCK" src/finam_core/pipelines/paper_pipeline.py
grep -q "wrong_direction_buy" src/finam_core/pipelines/paper_pipeline.py
grep -q "small_move" src/finam_core/pipelines/paper_pipeline.py

echo "TEST_NG_ROLLBACK_DIAGNOSTICS_V1_OK"
