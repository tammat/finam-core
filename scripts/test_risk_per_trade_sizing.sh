#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile \
  src/finam_core/runtime/risk_per_trade_sizing.py \
  src/scripts/run_risk_per_trade_sizing.py

python - <<'PY'
from finam_core.runtime.risk_per_trade_sizing import RiskPerTradeSizer

s = RiskPerTradeSizer()

r = s.size(
    equity=100000,
    risk_pct=0.01,
    entry_price=100,
    stop_loss=95,
    max_position_value=20000,
)

assert r.allowed is True
assert r.qty == 200
assert r.risk_rub == 1000
assert r.capital_used == 20000

blocked = s.size(
    equity=100000,
    risk_pct=0.01,
    entry_price=100,
    stop_loss=100,
    max_position_value=20000,
)

assert blocked.allowed is False

print("OK: risk per trade sizing")
PY
