#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core

PY_BIN="${PY_BIN:-/opt/finam-core/venv/bin/python}"
if [[ ! -x "$PY_BIN" ]]; then
  PY_BIN="$(command -v python3)"
fi

echo "TEST_NG_SIGNAL_SOURCE_PROPAGATION_V2_START"

"$PY_BIN" -m py_compile src/finam_core/pipelines/paper_pipeline.py

grep -q "NG_SIGNAL_SOURCE_PROPAGATION_V2" src/finam_core/pipelines/paper_pipeline.py
grep -q "_fill_intent_payload_by_fill_id" src/finam_core/pipelines/paper_pipeline.py
grep -q "PIPE_NG_SIGNAL_SOURCE_RESTORED" src/finam_core/pipelines/paper_pipeline.py

if grep -q "NG_SIGNAL_ID_PROPAGATION_V1" src/finam_core/pipelines/paper_pipeline.py; then
  echo "OLD_NG_SIGNAL_ID_PROPAGATION_V1_STILL_PRESENT"
  exit 1
fi

echo "TEST_NG_SIGNAL_SOURCE_PROPAGATION_V2_OK"
