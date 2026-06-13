#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core

echo "TEST_ENERGY_CLUSTER_BLOCK_BYPASS_PAPER_V1_START"

python3 -m py_compile src/finam_core/pipelines/paper_pipeline.py

grep -q "PIPE_CLUSTER_BLOCK_ADVISORY_CONTINUE" src/finam_core/pipelines/paper_pipeline.py
grep -q "ENABLE_PAPER_CLUSTER_BLOCK_BYPASS_V1" src/finam_core/pipelines/paper_pipeline.py
grep -q "PAPER_CLUSTER_BLOCK_BYPASS_SYMBOLS" src/finam_core/pipelines/paper_pipeline.py

echo "TEST_ENERGY_CLUSTER_BLOCK_BYPASS_PAPER_V1_OK"
