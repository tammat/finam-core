#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python3 -m py_compile src/scripts/analytics/build_runtime_problem_audit_v1.py

python3 src/scripts/analytics/build_runtime_problem_audit_v1.py | tee /tmp/runtime_problem_audit_v1.log

grep -q "VERDICT=OK" /tmp/runtime_problem_audit_v1.log
grep -q "SUMMARY" /tmp/runtime_problem_audit_v1.log

echo RUNTIME_PROBLEM_AUDIT_V1_OK
