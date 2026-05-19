#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile \
  src/finam_core/runtime/capital_growth_portfolio_governor.py \
  src/scripts/run_capital_growth_portfolio_governor.py \
  src/scripts/analyze_watch_candidates_runtime.py

python - <<'PY'
from finam_core.runtime.capital_growth_portfolio_governor import (
    CapitalGrowthPortfolioGovernor,
)

g = CapitalGrowthPortfolioGovernor()

ok = g.check(active_growth_trades=1, max_active_growth_trades=3)
assert ok.allowed is True

blocked = g.check(active_growth_trades=3, max_active_growth_trades=3)
assert blocked.allowed is False

print("OK: capital growth portfolio governor")
PY
