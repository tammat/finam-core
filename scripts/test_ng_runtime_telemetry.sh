#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH="${PYTHONPATH:-src}"

python -m py_compile src/scripts/build_ng_runtime_telemetry.py

grep -q "ng_runtime_telemetry" src/scripts/build_ng_runtime_telemetry.py
grep -q "runtime_governance_decisions" src/scripts/build_ng_runtime_telemetry.py
grep -q "NG_RUNTIME_TELEMETRY_SUMMARY" src/scripts/build_ng_runtime_telemetry.py

echo "TEST_NG_RUNTIME_TELEMETRY_OK"
