#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python - <<'PY'
from finam_core.execution.protection_level_calculator import ProtectionLevelCalculator

c = ProtectionLevelCalculator()

long_levels = c.calculate(
    symbol="BRM6@RTSX",
    entry_side="BUY",
    entry_price=103.20,
    atr=0.50,
    equity=400000,
    risk_pct=0.005,
    stop_atr_mult=2.0,
    reward_risk=2.0,
    max_qty=1,
    tick_size=0.01,
)

assert long_levels.exit_side == "SELL", long_levels
assert long_levels.stop_loss_price == 102.20, long_levels
assert long_levels.take_profit_price == 105.20, long_levels
assert long_levels.qty == 1, long_levels

short_levels = c.calculate(
    symbol="BRM6@RTSX",
    entry_side="SELL",
    entry_price=101.00,
    atr=0.40,
    equity=400000,
    risk_pct=0.005,
    stop_atr_mult=2.0,
    reward_risk=2.0,
    max_qty=1,
    tick_size=0.01,
)

assert short_levels.exit_side == "BUY", short_levels
assert short_levels.stop_loss_price == 101.80, short_levels
assert short_levels.take_profit_price == 99.40, short_levels
assert short_levels.qty == 1, short_levels

print("PROTECTION_LEVEL_CALCULATOR_OK")
PY
