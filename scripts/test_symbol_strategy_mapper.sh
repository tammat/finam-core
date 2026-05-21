#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH="${PYTHONPATH:-src}"

python - <<'PY'
from finam_core.analytics.symbol_strategy_mapper import map_symbol_to_strategy

assert map_symbol_to_strategy("BRM6@RTSX") == "br_conservative_breakout"
assert map_symbol_to_strategy("NGH6@RTSX") == "ng_volatility_breakout"
assert map_symbol_to_strategy("SBER@MISX") == "strategy_stack"
assert map_symbol_to_strategy("PLZL@MISX") == "strategy_stack"
assert map_symbol_to_strategy("SiM6@RTSX") == "futures_strategy_stack"

print("TEST_SYMBOL_STRATEGY_MAPPER_OK")
PY
