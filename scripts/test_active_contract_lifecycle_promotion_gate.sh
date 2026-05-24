#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile \
  src/finam_core/research/active_contract_lifecycle_filter.py \
  src/scripts/runtime/apply_active_contract_lifecycle_filter.py

grep -q "PROMOTED_RUNTIME" src/scripts/runtime/apply_active_contract_lifecycle_filter.py
grep -q "closed_trade_quality_stats" src/scripts/runtime/apply_active_contract_lifecycle_filter.py
grep -q "ACTIVE_CONTRACT_PROMOTION_DOWNGRADED" src/scripts/runtime/apply_active_contract_lifecycle_filter.py
grep -q "lifecycle_filter_downgraded" src/scripts/runtime/apply_active_contract_lifecycle_filter.py

echo "ACTIVE_CONTRACT_LIFECYCLE_PROMOTION_GATE_TEST_OK"
