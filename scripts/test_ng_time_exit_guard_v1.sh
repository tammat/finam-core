#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core

PY_BIN="${PY_BIN:-/opt/finam-core/venv/bin/python}"

if [[ ! -x "$PY_BIN" ]]; then
  PY_BIN="$(command -v python3)"
fi

echo "TEST_NG_TIME_EXIT_GUARD_V1_START"

"$PY_BIN" -m py_compile \
  src/finam_core/pipelines/paper_pipeline.py \
  src/finam_core/execution/exit_lifecycle_manager.py

grep -q "PIPE_NG_TIME_EXIT_GUARD" src/finam_core/pipelines/paper_pipeline.py
grep -q "NG_MIN_HOLD_SEC" src/finam_core/pipelines/paper_pipeline.py
grep -q "opened_at_ts" src/finam_core/pipelines/paper_pipeline.py

echo "TEST_NG_TIME_EXIT_GUARD_V1_OK"
