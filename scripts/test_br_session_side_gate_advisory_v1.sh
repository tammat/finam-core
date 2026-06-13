#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core

echo "TEST_BR_SESSION_SIDE_GATE_ADVISORY_V1_START"

python3 -m py_compile src/finam_core/pipelines/paper_pipeline.py

grep -q "ENABLE_BR_SESSION_SIDE_GATE_ADVISORY_V1" src/finam_core/pipelines/paper_pipeline.py
grep -q "PIPE_BR_SESSION_SIDE_GATE_ADVISORY_CONTINUE" src/finam_core/pipelines/paper_pipeline.py

echo "TEST_BR_SESSION_SIDE_GATE_ADVISORY_V1_OK"
