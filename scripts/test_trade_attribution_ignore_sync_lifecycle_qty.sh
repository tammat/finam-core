#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile \
  src/finam_core/analytics/trade_attribution_v2_repository.py \
  src/scripts/build_trade_attribution_v2.py

grep -q "SYNC_LIFECYCLE_QTY" \
  src/finam_core/analytics/trade_attribution_v2_repository.py

echo "TRADE_ATTRIBUTION_IGNORE_SYNC_LIFECYCLE_QTY_TEST_OK"
