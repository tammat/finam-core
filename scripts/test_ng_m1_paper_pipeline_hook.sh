#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH="${PYTHONPATH:-src}"

python -m py_compile src/finam_core/pipelines/paper_pipeline.py

grep -q "NgConservativeBreakoutM1" src/finam_core/pipelines/paper_pipeline.py
grep -q "_process_ng_m1_closed_bar_for_paper_signal" src/finam_core/pipelines/paper_pipeline.py
grep -q "ENABLE_NG_CONSERVATIVE_BREAKOUT_M1" src/finam_core/pipelines/paper_pipeline.py

echo "TEST_NG_M1_PAPER_PIPELINE_HOOK_OK"
