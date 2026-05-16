#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile src/scripts/runtime_rebalance_loop.py

python - <<'PY'
from pathlib import Path

text = Path("src/scripts/runtime_rebalance_loop.py").read_text(encoding="utf-8")

checks = [
    "aggregate_continuous_smart_money.py",
    "classify_institutional_flow_regime.py",
    "select_cross_contract_liquidity.py",
    "update_market_opportunity_metrics.py",
    "update_dynamic_watchlist_from_opportunities.py",
]

for c in checks:
    assert c in text, c

agg = text.find("aggregate_continuous_smart_money.py")
flow = text.find("classify_institutional_flow_regime.py")
liq = text.find("select_cross_contract_liquidity.py")
metrics = text.find("update_market_opportunity_metrics.py")
watchlist = text.find("update_dynamic_watchlist_from_opportunities.py")

assert agg < flow < liq < metrics < watchlist

print("OK: runtime rebalance includes cross contract liquidity in correct order")
PY
