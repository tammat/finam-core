#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH="${PYTHONPATH:-src}"

python -m py_compile src/scripts/audit_strategy_universe.py

echo "TEST_AUDIT_STRATEGY_UNIVERSE_COMPILE_OK"
