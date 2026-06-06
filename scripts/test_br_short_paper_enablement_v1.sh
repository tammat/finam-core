#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python3 -m py_compile src/finam_core/pipelines/paper_pipeline.py

grep -q "br_short_paper_enablement_gate_v1" src/finam_core/pipelines/paper_pipeline.py
grep -q "PIPE_BR_SHORT_PAPER_ALLOWED" src/finam_core/pipelines/paper_pipeline.py
grep -q "PIPE_BR_SHORT_PAPER_SHADOW_ONLY" src/finam_core/pipelines/paper_pipeline.py
grep -q "PIPE_BR_SHORT_PAPER_BLOCK" src/finam_core/pipelines/paper_pipeline.py

echo BR_SHORT_PAPER_ENABLEMENT_V1_OK
