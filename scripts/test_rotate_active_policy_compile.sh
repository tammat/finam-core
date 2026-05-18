#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile \
  src/scripts/rotate_active_policy.py \
  src/finam_core/research/policy_decision_repository.py

python src/scripts/rotate_active_policy.py --help >/dev/null

echo "OK: rotate active policy compile"
