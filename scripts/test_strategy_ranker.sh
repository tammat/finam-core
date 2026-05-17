#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile src/finam_core/analytics/strategy_ranker.py

python - <<'PY'
from decimal import Decimal

from finam_core.analytics.strategy_ranker import (
    StrategyRanker,
    StrategyScorecardRow,
)

ranker = StrategyRanker(min_trades=30)

good = StrategyScorecardRow(
    strategy="BR_CONSERVATIVE_BREAKOUT",
    symbol="BRM6@RTSX",
    timeframe="INTRADAY",
    trades=121,
    net_pnl=Decimal("374"),
    winrate=Decimal("0.8678"),
    profit_factor=Decimal("233.2181"),
    expectancy=Decimal("3.0909"),
)

bad = StrategyScorecardRow(
    strategy="USDRUB_REGIME",
    symbol="USDRUBF@RTSX",
    timeframe="unknown",
    trades=70,
    net_pnl=Decimal("-10.21"),
    winrate=Decimal("0"),
    profit_factor=Decimal("0"),
    expectancy=Decimal("-0.1459"),
)

thin = StrategyScorecardRow(
    strategy="NEW_STRATEGY",
    symbol="SBER@MISX",
    timeframe="M5",
    trades=5,
    net_pnl=Decimal("100"),
    winrate=Decimal("0.8"),
    profit_factor=Decimal("2"),
    expectancy=Decimal("20"),
)

assert ranker.rank(good).decision == "ENABLE"
assert ranker.rank(bad).decision == "DISABLE"
assert ranker.rank(thin).decision == "WATCH"

print("OK: strategy ranker v1")
PY
