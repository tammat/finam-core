#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core

grep -q "REPLAY_DISABLE_BR_REGIME" src/finam_core/pipelines/paper_pipeline.py
grep -q "REPLAY_BR_REGIME_DISABLED" src/finam_core/pipelines/paper_pipeline.py
grep -q "from dataclasses import replace" src/finam_core/pipelines/paper_pipeline.py
grep -q "decision = replace" src/finam_core/pipelines/paper_pipeline.py
! grep -q "decision.allowed = True" src/finam_core/pipelines/paper_pipeline.py

python -m py_compile src/finam_core/pipelines/paper_pipeline.py

echo "REPLAY_DISABLE_BR_REGIME_TEST_OK"
