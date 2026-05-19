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
    "update_market_opportunity_metrics.py",
]

for c in checks:
    assert c in text, c

agg_pos = text.find("aggregate_continuous_smart_money.py")
flow_pos = text.find("classify_institutional_flow_regime.py")
metrics_pos = text.find("update_market_opportunity_metrics.py")

assert agg_pos < flow_pos < metrics_pos

print("OK: runtime rebalance institutional flow ordering")
PY
