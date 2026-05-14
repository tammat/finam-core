#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile \
  src/finam_core/pipelines/paper_pipeline.py \
  src/finam_core/strategy/strategy_factory.py \
  src/finam_core/strategy/symbol_strategy_map.py \
  src/finam_core/strategy/ng/ng_volatility_breakout.py \
  src/finam_core/strategy/fx/usdrub_regime_strategy.py \
  src/finam_core/strategy/equities/mean_reversion_equity.py \
  src/finam_core/strategy/equities/trend_pullback_equity.py

python - <<'PY'
from finam_core.strategy.strategy_factory import StrategyFactory

expected = {
    "BRM6@RTSX": "BrConservativeBreakout",
    "NGK6@RTSX": "NGVolatilityBreakout",
    "USDRUBF@RTSX": "USDRUBRegimeStrategy",
    "LKOH@MISX": "MeanReversionEquity",
    "PLZL@MISX": "TrendPullbackEquity",
}

for symbol, cls in expected.items():
    obj = StrategyFactory.create(symbol)
    got = obj.__class__.__name__

    assert got == cls, (symbol, got, cls)

    print(f"{symbol} -> {got}")

print("OK: strategy map pipeline compile")
PY
