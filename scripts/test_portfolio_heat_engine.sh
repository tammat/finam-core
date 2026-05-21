#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH="${PYTHONPATH:-src}"

python - <<'PY'
from finam_core.portfolio.portfolio_heat_engine import evaluate_portfolio_heat

normal = evaluate_portfolio_heat(total_heat=0.5)
assert normal.status == "NORMAL"
assert normal.risk_multiplier == 1.0
assert normal.allow_new_entries is True

elevated = evaluate_portfolio_heat(total_heat=0.8)
assert elevated.status == "ELEVATED"
assert elevated.risk_multiplier == 0.75
assert elevated.allow_new_entries is True

high = evaluate_portfolio_heat(total_heat=1.05)
assert high.status == "HIGH"
assert high.risk_multiplier == 0.5
assert high.allow_new_entries is True

critical = evaluate_portfolio_heat(total_heat=1.4)
assert critical.status == "CRITICAL"
assert critical.risk_multiplier == 0.0
assert critical.allow_new_entries is False

print("TEST_PORTFOLIO_HEAT_ENGINE_OK")
PY

python -m py_compile src/finam_core/portfolio/portfolio_heat_engine.py
