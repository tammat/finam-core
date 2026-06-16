#!/usr/bin/env bash
set -euo pipefail

cd "$(git rev-parse --show-toplevel)"
export PYTHONPATH=src

python3 -m py_compile src/finam_core/pipelines/paper_pipeline.py

grep -q 'NG_PAPER_TRADE_IDENTITY_ENFORCEMENT_V1' src/finam_core/pipelines/paper_pipeline.py
grep -q 'NG_PAPER_TRADE_IDENTITY_MISSING' src/finam_core/pipelines/paper_pipeline.py
grep -q 'raw_intent\["strategy"\]' src/finam_core/pipelines/paper_pipeline.py
grep -q 'raw_intent\["timeframe"\]' src/finam_core/pipelines/paper_pipeline.py
grep -q 'raw_intent\["origin"\] = "paper"' src/finam_core/pipelines/paper_pipeline.py
grep -q 'raw_intent\["trade_source"\] = "paper"' src/finam_core/pipelines/paper_pipeline.py

echo TEST_NG_PAPER_TRADE_IDENTITY_ENFORCEMENT_V1_OK
