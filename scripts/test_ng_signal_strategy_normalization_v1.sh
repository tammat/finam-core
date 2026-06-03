#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core
PY_BIN="${PY_BIN:-/opt/finam-core/venv/bin/python}"
[[ -x "$PY_BIN" ]] || PY_BIN="$(command -v python3)"

echo "TEST_NG_SIGNAL_STRATEGY_NORMALIZATION_V1_START"

"$PY_BIN" -m py_compile src/finam_core/pipelines/paper_pipeline.py

grep -q "NG_SIGNAL_STRATEGY_NORMALIZATION_V1" src/finam_core/pipelines/paper_pipeline.py
grep -q "PIPE_NG_SIGNAL_STRATEGY_NORMALIZED" src/finam_core/pipelines/paper_pipeline.py
grep -q "UNKNOWN_STRATEGY" src/finam_core/pipelines/paper_pipeline.py

echo "TEST_NG_SIGNAL_STRATEGY_NORMALIZATION_V1_OK"
