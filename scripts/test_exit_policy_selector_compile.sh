#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH="${PYTHONPATH:-src}"

python -m py_compile \
  src/finam_core/analytics/exit_policy_selector.py \
  scripts/analytics/select_exit_policy.py

echo "TEST_EXIT_POLICY_SELECTOR_COMPILE_OK"
