#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python - <<'PY'
from finam_core.risk.portfolio_risk_gate import PortfolioRiskGate

g = PortfolioRiskGate()

ok = g.evaluate(
    equity=100000,
    total_exposure=20000,
    symbol_exposure=5000,
    used_margin=15000,
    daily_pnl=-500,
    peak_equity=102000,
    current_equity=100000,
)
assert ok.allowed is True, ok

heat = g.evaluate(
    equity=100000,
    total_exposure=50000,
    symbol_exposure=5000,
    used_margin=15000,
    daily_pnl=0,
    peak_equity=100000,
    current_equity=100000,
)
assert heat.allowed is False, heat
assert heat.reason == "portfolio_heat", heat

margin = g.evaluate(
    equity=100000,
    total_exposure=10000,
    symbol_exposure=5000,
    used_margin=70000,
    daily_pnl=0,
    peak_equity=100000,
    current_equity=100000,
)
assert margin.allowed is False, margin
assert margin.reason == "margin_utilization", margin

dd = g.evaluate(
    equity=100000,
    total_exposure=10000,
    symbol_exposure=5000,
    used_margin=15000,
    daily_pnl=0,
    peak_equity=120000,
    current_equity=100000,
    max_drawdown_pct=0.10,
)
assert dd.allowed is False, dd
assert dd.reason == "drawdown", dd

print("PORTFOLIO_RISK_GATE_OK")
PY
