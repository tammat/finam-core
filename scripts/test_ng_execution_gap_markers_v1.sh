#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core

echo "TEST_NG_EXECUTION_GAP_MARKERS_V1_START"

python3 -m py_compile src/finam_core/pipelines/paper_pipeline.py

grep -q "PIPE_NG_EXEC_TRACE_AFTER_RISK_OK" src/finam_core/pipelines/paper_pipeline.py
grep -q "PIPE_NG_EXEC_TRACE_BEFORE_PORTFOLIO_GATE" src/finam_core/pipelines/paper_pipeline.py

echo "TEST_NG_EXECUTION_GAP_MARKERS_V1_OK"
