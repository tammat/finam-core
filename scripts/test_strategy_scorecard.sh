#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile src/finam_core/analytics/strategy_scorecard.py

python - <<'PY'
from decimal import Decimal

from finam_core.analytics.strategy_scorecard import (
    StrategyScorecardCalculator,
    TradeResult,
)

trades = [
    TradeResult("BRM6@RTSX", "br_breakout", "M5", Decimal("100"), Decimal("5"), Decimal("1.5")),
    TradeResult("BRM6@RTSX", "br_breakout", "M5", Decimal("-40"), Decimal("5"), Decimal("-0.7")),
    TradeResult("BRM6@RTSX", "br_breakout", "M5", Decimal("80"), Decimal("5"), Decimal("1.2")),
]

score = StrategyScorecardCalculator().calculate(trades)

assert score.trades == 3
assert score.gross_pnl == Decimal("140")
assert score.net_pnl == Decimal("125")
assert score.commission_total == Decimal("15")
assert score.winrate == Decimal("2") / Decimal("3")
assert score.expectancy == Decimal("125") / Decimal("3")
assert score.max_drawdown == Decimal("-45")

print("OK: strategy scorecard v1")
PY
