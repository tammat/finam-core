#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile \
  src/finam_core/strategy/dynamic_strategy_resolver.py \
  src/finam_core/strategy/strategy_factory.py \
  src/finam_core/strategy/equities/volatility_breakout_equity.py

python - <<'PY'
from finam_core.strategy.dynamic_strategy_resolver import DynamicStrategyResolver
from finam_core.strategy.strategy_factory import StrategyFactory
from finam_core.strategy.equities.volatility_breakout_equity import VolatilityBreakoutEquity


class Cursor:
    def execute(self, sql, params):
        assert "dynamic_watchlist" in sql
        assert params == ("SBER@MISX",)

    def fetchone(self):
        return ("VOLATILITY_BREAKOUT_EQUITY",)

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


class Conn:
    def cursor(self):
        return Cursor()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


class PgLogger:
    def _connect(self):
        return Conn()


resolver = DynamicStrategyResolver(PgLogger())
strategy_name = resolver.strategy_for_symbol("SBER@MISX")

assert strategy_name == "VOLATILITY_BREAKOUT_EQUITY"

strategy = StrategyFactory.create("SBER@MISX", strategy_name=strategy_name)
assert isinstance(strategy, VolatilityBreakoutEquity)

fallback = DynamicStrategyResolver(None).strategy_for_symbol("PLZL@MISX")
assert fallback == "TREND_PULLBACK_EQUITY"

print("OK: dynamic strategy resolver and StrategyFactory override")
PY
