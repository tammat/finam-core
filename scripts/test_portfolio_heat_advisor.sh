#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH="${PYTHONPATH:-src}"

python - <<'PY'
from finam_core.runtime.portfolio_heat_advisor import PortfolioHeatAdvice

advice = PortfolioHeatAdvice(
    status="HIGH",
    heat=1.05,
    risk_multiplier=0.5,
    allow_new_entries=True,
    reason="portfolio_heat_high_reduce_risk",
)

assert advice.status == "HIGH"
assert advice.risk_multiplier == 0.5
assert advice.allow_new_entries is True
assert advice.source == "portfolio_heat_events"

print("TEST_PORTFOLIO_HEAT_ADVISOR_OK")
PY

python -m py_compile src/finam_core/runtime/portfolio_heat_advisor.py
