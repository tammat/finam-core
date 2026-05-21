#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH="${PYTHONPATH:-src}"

python -m py_compile scripts/analytics/inspect_trades_schema.py

echo "TEST_ANALYTICS_INSPECT_TRADES_SCHEMA_COMPILE_OK"
