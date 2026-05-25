#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile \
  src/finam_core/analytics/symbol_strategy_mapper.py \
  src/finam_core/analytics/closed_trade_reconstruction_v2_repository.py \
  src/scripts/build_trade_attribution_v2.py

if grep -R -n "br_conservative_breakout" \
  src/finam_core/analytics/symbol_strategy_mapper.py \
  src/finam_core/analytics/closed_trade_reconstruction_v2_repository.py; then
  echo "ERROR: lowercase BR strategy still present"
  exit 1
fi

echo "BR_STRATEGY_CANONICAL_NAME_TEST_OK"
