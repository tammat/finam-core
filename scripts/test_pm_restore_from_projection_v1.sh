#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core

PY_BIN="${PY_BIN:-/opt/finam-core/venv/bin/python}"
[[ -x "$PY_BIN" ]] || PY_BIN="$(command -v python3)"

echo "TEST_PM_RESTORE_FROM_PROJECTION_V1_START"

"$PY_BIN" -m py_compile src/finam_core/pipelines/paper_pipeline.py

grep -q "_restore_pm_position_from_projection_v1" src/finam_core/pipelines/paper_pipeline.py
grep -q "PIPE_PM_RESTORED_FROM_PROJECTION" src/finam_core/pipelines/paper_pipeline.py
grep -q "state->>'qty'" src/finam_core/pipelines/paper_pipeline.py

echo "TEST_PM_RESTORE_FROM_PROJECTION_V1_OK"
