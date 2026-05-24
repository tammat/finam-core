#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH="${PYTHONPATH:-src}"

python -m py_compile src/scripts/build_ng_runtime_regime_policy.py

grep -q "ng_runtime_regime_policy" src/scripts/build_ng_runtime_regime_policy.py
grep -q "allow_runtime" src/scripts/build_ng_runtime_regime_policy.py
grep -q "NG_RUNTIME_REGIME_POLICY_SUMMARY" src/scripts/build_ng_runtime_regime_policy.py

echo "TEST_NG_RUNTIME_REGIME_POLICY_OK"
