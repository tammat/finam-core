#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile \
  src/finam_core/research/policy_decision_repository.py \
  src/scripts/save_policy_decision.py

python src/scripts/save_policy_decision.py --help >/dev/null

echo "OK: policy decision registry"
