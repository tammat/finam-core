#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python3 -m py_compile \
  src/finam_core/governance/runtime_guard_reader.py \
  src/scripts/runtime/test_runtime_guard_reader_v1.py

python3 src/scripts/runtime/test_runtime_guard_reader_v1.py

echo RUNTIME_GUARD_READER_V1_OK
