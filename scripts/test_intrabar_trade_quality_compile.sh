#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH="${PYTHONPATH:-src}"

python -m py_compile \
  src/finam_core/analytics/intrabar_mae_mfe.py \
  src/finam_core/analytics/intrabar_repository.py \
  scripts/analytics/build_intrabar_trade_quality.py

echo "TEST_INTRABAR_TRADE_QUALITY_COMPILE_OK"
