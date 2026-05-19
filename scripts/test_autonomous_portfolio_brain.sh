#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile \
  src/finam_core/runtime/autonomous_portfolio_brain.py \
  src/scripts/run_autonomous_portfolio_brain.py

python - <<'PY'
from finam_core.runtime.autonomous_portfolio_brain import (
    AutonomousPortfolioBrain,
)

b = AutonomousPortfolioBrain()

offensive = b.decide(
    equity=500000,
    drawdown_pct=0.02,
    runtime_winrate=0.61,
    market_breadth=0.72,
    runtime_stress="INFO",
    open_positions=2,
    daily_pnl_pct=0.01,
    regime="trend_up_high_vol",
)

assert offensive.portfolio_phase == "OFFENSIVE"

recovery = b.decide(
    equity=500000,
    drawdown_pct=0.07,
    runtime_winrate=0.52,
    market_breadth=0.50,
    runtime_stress="INFO",
    open_positions=5,
    daily_pnl_pct=-0.03,
    regime="range",
)

assert recovery.portfolio_phase == "RECOVERY"

preserve = b.decide(
    equity=500000,
    drawdown_pct=0.12,
    runtime_winrate=0.40,
    market_breadth=0.20,
    runtime_stress="CRITICAL",
    open_positions=8,
    daily_pnl_pct=-0.05,
    regime="range",
)

assert preserve.portfolio_phase == "CAPITAL_PRESERVATION"

print("OK: autonomous portfolio brain")
PY
