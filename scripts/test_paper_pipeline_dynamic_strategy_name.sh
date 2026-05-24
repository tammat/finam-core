#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH="${PYTHONPATH:-src}"

python -m py_compile src/finam_core/pipelines/paper_pipeline.py

grep -q "strategy=br_strategy" src/finam_core/pipelines/paper_pipeline.py
grep -q '"strategy": br_strategy' src/finam_core/pipelines/paper_pipeline.py

echo "TEST_PAPER_PIPELINE_DYNAMIC_STRATEGY_NAME_OK"
