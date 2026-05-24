#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH="${PYTHONPATH:-src}"

python -m py_compile src/finam_core/strategy/symbol_strategy_map.py

python - <<'PY'
from finam_core.strategy.symbol_strategy_map import SYMBOL_STRATEGY_MAP

assert SYMBOL_STRATEGY_MAP["NGM6@RTSX"] == "NG_CONSERVATIVE_BREAKOUT_M1"
assert SYMBOL_STRATEGY_MAP["NGN6@RTSX"] == "NG_CONSERVATIVE_BREAKOUT_M1"
assert SYMBOL_STRATEGY_MAP["BRM6@RTSX"] == "BR_CONSERVATIVE_BREAKOUT"

print("TEST_SYMBOL_STRATEGY_MAP_NG_M1_OK")
PY
