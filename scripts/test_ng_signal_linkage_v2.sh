#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core

PY_BIN="${PY_BIN:-/opt/finam-core/venv/bin/python}"
if [[ ! -x "$PY_BIN" ]]; then
  PY_BIN="$(command -v python3)"
fi

echo "TEST_NG_SIGNAL_LINKAGE_V2_START"

"$PY_BIN" -m py_compile src/finam_core/pipelines/paper_pipeline.py

grep -q "NG_SIGNAL_LINKAGE_V2" src/finam_core/pipelines/paper_pipeline.py
grep -q "source_signal_id" src/finam_core/pipelines/paper_pipeline.py
grep -q "strategy_signal" src/finam_core/pipelines/paper_pipeline.py
grep -q "paper_fill_fallback" src/finam_core/pipelines/paper_pipeline.py

echo "TEST_NG_SIGNAL_LINKAGE_V2_OK"
