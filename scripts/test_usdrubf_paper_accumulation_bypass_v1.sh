#!/usr/bin/env bash
set -euo pipefail

cd "$(git rev-parse --show-toplevel)"

python3 -m py_compile src/finam_core/pipelines/paper_pipeline.py

grep -q "ENABLE_USDRUBF_PAPER_ACCUMULATION_BYPASS_V1" src/finam_core/pipelines/paper_pipeline.py
grep -q "USDRUBF_PAPER_ACCUMULATION_BYPASS" src/finam_core/pipelines/paper_pipeline.py
grep -q "REAL_TRADING_ENABLED" src/finam_core/pipelines/paper_pipeline.py
grep -q "runtime_allow=0" src/finam_core/pipelines/paper_pipeline.py
grep -q "execution_enabled=0" src/finam_core/pipelines/paper_pipeline.py

echo TEST_USDRUBF_PAPER_ACCUMULATION_BYPASS_V1_OK
