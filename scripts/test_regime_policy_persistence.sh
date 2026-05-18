#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile \
  src/finam_core/research/regime_policy_repository.py \
  src/finam_core/research/regime_risk_policy.py \
  src/scripts/build_regime_risk_policy.py

python src/scripts/build_regime_risk_policy.py --help >/dev/null

echo "OK: regime policy persistence"
