#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile src/scripts/runtime/build_regime_runtime_overrides.py

grep -q "is_default_policy" src/scripts/runtime/build_regime_runtime_overrides.py
grep -q "override.runtime_action == \"NEUTRAL\"" src/scripts/runtime/build_regime_runtime_overrides.py
grep -q "is_default_policy" scripts/migrate_runtime_regime_overrides_default_policy.sh

echo "RUNTIME_REGIME_OVERRIDES_DEFAULT_POLICY_TEST_OK"
