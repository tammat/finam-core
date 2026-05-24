#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH="${PYTHONPATH:-src}"

python -m py_compile \
  src/scripts/build_session_runtime_policy.py \
  src/scripts/apply_session_runtime_gate.py

grep -q "session_runtime_policy" src/scripts/build_session_runtime_policy.py
grep -q "SESSION_BLOCKED" src/scripts/apply_session_runtime_gate.py
grep -q "classify_futures_session" src/scripts/apply_session_runtime_gate.py

echo "TEST_SESSION_RUNTIME_GATE_OK"
