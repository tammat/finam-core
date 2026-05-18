#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile \
  src/scripts/validate_campaign_statistics.py \
  src/finam_core/analytics/statistical_validation_engine.py

python src/scripts/validate_campaign_statistics.py --help >/dev/null

echo "OK: validate_campaign_statistics compile"
