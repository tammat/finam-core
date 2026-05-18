#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile \
  src/finam_core/research/policy_impact_repository.py \
  src/scripts/save_policy_impact_report.py

python src/scripts/save_policy_impact_report.py --help >/dev/null

echo "OK: policy impact report"
