#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH="${PYTHONPATH:-src}"

python -m py_compile src/scripts/build_ng_m1_runtime_policy.py

grep -q "ng_m1_runtime_policy" src/scripts/build_ng_m1_runtime_policy.py
grep -q "EXCLUDED_SESSIONS" src/scripts/build_ng_m1_runtime_policy.py
grep -q "NG_M1_RUNTIME_POLICY_SUMMARY" src/scripts/build_ng_m1_runtime_policy.py

echo "TEST_NG_M1_RUNTIME_POLICY_OK"
