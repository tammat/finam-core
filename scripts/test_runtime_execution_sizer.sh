#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH="${PYTHONPATH:-src}"

python -m py_compile src/finam_core/runtime/runtime_execution_sizer.py

grep -q "runtime_capital_allocator" src/finam_core/runtime/runtime_execution_sizer.py
grep -q "RuntimeSizingDecision" src/finam_core/runtime/runtime_execution_sizer.py
grep -q "runtime_sizing_ok" src/finam_core/runtime/runtime_execution_sizer.py

echo "TEST_RUNTIME_EXECUTION_SIZER_OK"
