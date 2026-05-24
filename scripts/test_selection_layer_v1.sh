#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile \
  src/finam_core/research/selection_runner.py

echo "SELECTION_LAYER_V1_TEST_OK"
