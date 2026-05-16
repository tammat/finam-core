#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile \
  src/finam_core/data/moex_opportunity_scanner.py

python - <<'PY'
from finam_core.data.moex_opportunity_scanner import (
    MOEXOpportunityScanner,
)

s = MOEXOpportunityScanner()

x = s.evaluate(
    symbol="OZON@MISX",
    atr_pct=0.015,
    rvol=2.0,
    turnover=2_000_000_000,
    spread_pct=0.001,
    regime="trend_up_high_vol",
)

assert x is not None
assert x.strategy == "VOLATILITY_BREAKOUT_EQUITY"

y = s.evaluate(
    symbol="SBER@MISX",
    atr_pct=0.009,
    rvol=1.3,
    turnover=1_000_000_000,
    spread_pct=0.001,
    regime="trend_up_low_vol",
)

assert y is not None
assert y.strategy == "TREND_PULLBACK_EQUITY"

z = s.evaluate(
    symbol="TRASH@MISX",
    atr_pct=0.02,
    rvol=3.0,
    turnover=1_000_000,
    spread_pct=0.02,
    regime="trend_up_high_vol",
)

assert z is None

ranked = s.rank([x, y])

assert ranked[0].opportunity_score >= ranked[1].opportunity_score
assert ranked[0].opportunity_score <= 1.0
assert ranked[1].opportunity_score <= 1.0

print("OK: MOEXOpportunityScanner")
PY
