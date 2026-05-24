#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH="${PYTHONPATH:-src}"

python -m py_compile src/scripts/build_runtime_capital_allocator.py

grep -q "runtime_capital_allocator" \
  src/scripts/build_runtime_capital_allocator.py

grep -q "RUNTIME_CAPITAL_ALLOCATOR_SUMMARY" \
  src/scripts/build_runtime_capital_allocator.py

echo "TEST_RUNTIME_CAPITAL_ALLOCATOR_OK"
