#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile \
  src/finam_core/orderflow/cross_contract_liquidity_allocator.py \
  src/scripts/select_cross_contract_liquidity.py

python - <<'PY'
from pathlib import Path

text = Path("src/finam_core/orderflow/cross_contract_liquidity_allocator.py").read_text(encoding="utf-8")

checks = [
    "CrossContractLiquidityAllocator",
    "BR_CONT",
    "BRM6@RTSX",
    "BRN6@RTSX",
    "smart_money_feature_events",
    "market_opportunity_metrics",
    "preferred_symbol",
]

for c in checks:
    assert c in text, c

print("OK: CrossContractLiquidityAllocator static check")
PY
