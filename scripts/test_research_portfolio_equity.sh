#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile \
  src/finam_core/research/research_portfolio_equity.py \
  src/scripts/build_research_portfolio_equity.py

python src/scripts/build_research_portfolio_equity.py --help >/dev/null

python - <<'PY'
from finam_core.research.research_portfolio_equity import (
    PortfolioTrade,
    ResearchPortfolioEquityCurve,
)

trades = [
    PortfolioTrade("A", "2025-01-01", 10.0, 0.5),
    PortfolioTrade("B", "2025-01-02", -4.0, 0.5),
    PortfolioTrade("A", "2025-01-03", 6.0, 0.5),
]

points = ResearchPortfolioEquityCurve().build(trades)

assert len(points) == 3
assert points[-1].equity == 6.0
assert min(p.drawdown for p in points) == -2.0

print("OK: research portfolio equity")
PY
