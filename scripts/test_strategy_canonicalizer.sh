#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH="${PYTHONPATH:-src}"

python -m py_compile \
  src/finam_core/research/strategy_canonicalizer.py \
  src/scripts/canonicalize_strategy_data.py

python - <<'PY'
from finam_core.research.strategy_canonicalizer import (
    canonicalize_strategy_name,
    canonicalize_timeframe,
)

assert canonicalize_strategy_name("br_conservative_breakout") == "BR_CONSERVATIVE_BREAKOUT"
assert canonicalize_strategy_name("br-conservative breakout") == "BR_CONSERVATIVE_BREAKOUT"
assert canonicalize_timeframe("m5") == "M5"

print("TEST_STRATEGY_CANONICALIZER_OK")
PY
