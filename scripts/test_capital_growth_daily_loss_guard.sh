#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile \
  src/finam_core/runtime/capital_growth_daily_loss_guard.py \
  src/scripts/run_capital_growth_daily_loss_guard.py

python - <<'PY'
from finam_core.runtime.capital_growth_daily_loss_guard import CapitalGrowthDailyLossGuard

g = CapitalGrowthDailyLossGuard()

ok = g.check(
    equity=100000,
    daily_pnl=-1000,
    max_daily_loss_pct=0.02,
)
assert ok.allowed is True

blocked = g.check(
    equity=100000,
    daily_pnl=-2500,
    max_daily_loss_pct=0.02,
)
assert blocked.allowed is False
assert blocked.daily_loss_pct == 0.025

print("OK: capital growth daily loss guard")
PY
