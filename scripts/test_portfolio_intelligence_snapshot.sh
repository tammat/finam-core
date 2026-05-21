#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH="${PYTHONPATH:-src}"

python - <<'PY'
from finam_core.portfolio.portfolio_intelligence_snapshot import (
    build_portfolio_intelligence_snapshot,
)

snapshot = build_portfolio_intelligence_snapshot(
    positions=[
        {
            "symbol": "BRM6@RTSX",
            "qty": 1.0,
            "avg_price": 100.0,
            "current_price": 110.0,
        },
        {
            "symbol": "SBER@MISX",
            "qty": 10.0,
            "avg_price": 300.0,
            "current_price": 310.0,
        },
    ],
    strategy_by_symbol={
        "BRM6@RTSX": "br_conservative_breakout",
        "SBER@MISX": "VOLATILITY_BREAKOUT_EQUITY",
    },
    regime_by_symbol={
        "BRM6@RTSX": "trend",
        "SBER@MISX": "range",
    },
    realized_pnl_by_symbol={
        "BRM6@RTSX": 5.0,
        "SBER@MISX": -10.0,
    },
    strategy_health_by_symbol={
        "BRM6@RTSX": "healthy",
        "SBER@MISX": "watch",
    },
    cash=1000.0,
)

assert len(snapshot.symbols) == 2
assert snapshot.total_exposure == 3210.0
assert snapshot.total_unrealized_pnl == 110.0
assert snapshot.total_realized_pnl == -5.0
assert snapshot.symbols[0].strategy == "br_conservative_breakout"
assert snapshot.symbols[1].strategy == "VOLATILITY_BREAKOUT_EQUITY"
assert snapshot.symbols[0].portfolio_weight > 0
assert snapshot.total_heat > 0

print("TEST_PORTFOLIO_INTELLIGENCE_SNAPSHOT_OK")
PY

python -m py_compile src/finam_core/portfolio/portfolio_intelligence_snapshot.py
