#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core

PY_BIN="${PY_BIN:-/opt/finam-core/venv/bin/python}"
[[ -x "$PY_BIN" ]] || PY_BIN="$(command -v python3)"

echo "TEST_PM_RESTORE_FROM_PROJECTION_V2_START"

"$PY_BIN" -m py_compile src/finam_core/pipelines/paper_pipeline.py

grep -q "positions — defaultdict(Position)" src/finam_core/pipelines/paper_pipeline.py
grep -q "pos = self.pm.positions\\[symbol\\]" src/finam_core/pipelines/paper_pipeline.py
grep -q "PIPE_PM_RESTORED_FROM_PROJECTION" src/finam_core/pipelines/paper_pipeline.py

echo "TEST_PM_RESTORE_FROM_PROJECTION_V2_OK"
