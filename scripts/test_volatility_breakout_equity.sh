#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile \
  src/finam_core/strategy/equities/volatility_breakout_equity.py \
  src/finam_core/signals/signal_intent.py

python - <<'PY'
from finam_core.strategy.equities.volatility_breakout_equity import (
    VolatilityBreakoutEquity,
    VolatilityBreakoutConfig,
)

s = VolatilityBreakoutEquity(
    VolatilityBreakoutConfig(
        lookback=3,
        min_atr_pct=0.005,
        volume_mult=1.2,
        stop_atr=1.0,
        take_atr=2.0,
        qty=1,
    )
)

assert s.on_quote("OZON@MISX", price=100, high=100, volume=1000, atr=1) is None
assert s.on_quote("OZON@MISX", price=101, high=101, volume=1000, atr=1) is None
assert s.on_quote("OZON@MISX", price=102, high=102, volume=1000, atr=1) is None

intent = s.on_quote(
    "OZON@MISX",
    price=104,
    high=104,
    volume=2000,
    atr=1.2,
    regime="trend_up_high_vol",
)

assert intent is not None
assert intent.symbol == "OZON@MISX"
assert intent.side == "BUY"
assert intent.strategy == "VOLATILITY_BREAKOUT_EQUITY"
assert intent.stop_price == 102.8
assert intent.take_profit == 106.4
assert intent.features["setup_type"] == "volatility_breakout"

print("OK: VolatilityBreakoutEquity")
PY
