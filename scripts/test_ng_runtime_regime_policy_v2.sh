#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH="${PYTHONPATH:-src}"

python -m py_compile src/scripts/build_ng_runtime_regime_policy_v2.py

grep -q "ng_runtime_regime_policy_v2" src/scripts/build_ng_runtime_regime_policy_v2.py
grep -q "regime_v2" src/scripts/build_ng_runtime_regime_policy_v2.py
grep -q "EXCLUDED_SESSIONS" src/scripts/build_ng_runtime_regime_policy_v2.py
grep -q "NG_RUNTIME_REGIME_POLICY_V2_SUMMARY" src/scripts/build_ng_runtime_regime_policy_v2.py

echo "TEST_NG_RUNTIME_REGIME_POLICY_V2_OK"
