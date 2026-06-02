#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core

PY_BIN="${PY_BIN:-/opt/finam-core/venv/bin/python}"

if [[ ! -x "$PY_BIN" ]]; then
  PY_BIN="$(command -v python3)"
fi

echo "TEST_RUNTIME_LOG_NOISE_GUARD_V1_START"

"$PY_BIN" -m py_compile \
  src/finam_core/pipelines/paper_pipeline.py \
  src/finam_core/execution/exit_lifecycle_manager.py

grep -q "RUNTIME_DEBUG_LOGS" src/finam_core/pipelines/paper_pipeline.py
grep -q "PIPE_POSITION_LIFECYCLE_STATE_LOADED" src/finam_core/pipelines/paper_pipeline.py
grep -q "PIPE_NG_TICK_ROUTE_NO_INTENT_CONTINUE_MTF" src/finam_core/pipelines/paper_pipeline.py
grep -q "PIPE_EXIT_ENGINE_CHECK" src/finam_core/pipelines/paper_pipeline.py
grep -q "PIPE_EXIT_ENGINE_CHECK" src/finam_core/execution/exit_lifecycle_manager.py

echo "TEST_RUNTIME_LOG_NOISE_GUARD_V1_OK"
