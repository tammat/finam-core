#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile src/finam_core/analytics/strategy_health_engine.py

python - <<'PY'
from finam_core.analytics.strategy_health_engine import StrategyHealthEngine, StrategyHealthInput

engine = StrategyHealthEngine(min_trades=3)

strong = engine.evaluate(StrategyHealthInput(
    symbol="BRM6@RTSX",
    strategy="BR_CONSERVATIVE_BREAKOUT_M5",
    trades=5,
    net_pnl=20.0,
    expectancy=4.0,
    winrate_pct=80.0,
    profit_factor=3.0,
))

assert strong.status == "УСИЛИТЬ", strong
assert strong.allow_trade is True
assert strong.watch_only is False
assert strong.risk_multiplier == 1.2
assert strong.score > 50

weak = engine.evaluate(StrategyHealthInput(
    symbol="BRM6@RTSX",
    strategy="BAD_STRATEGY",
    trades=5,
    net_pnl=-10.0,
    expectancy=-2.0,
    winrate_pct=20.0,
    profit_factor=0.2,
))

assert weak.status == "ОТКЛЮЧИТЬ", weak
assert weak.allow_trade is False
assert weak.watch_only is True
assert weak.risk_multiplier == 0.0

empty = engine.evaluate(StrategyHealthInput(
    symbol="BRM6@RTSX",
    strategy="NEW_STRATEGY",
    trades=1,
    net_pnl=5.0,
    expectancy=5.0,
    winrate_pct=100.0,
))

assert empty.status == "НЕДОСТАТОЧНО_ДАННЫХ", empty
assert empty.watch_only is True

print("OK: движок здоровья стратегий работает")
PY
