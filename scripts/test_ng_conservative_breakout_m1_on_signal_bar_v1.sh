#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core
export PYTHONPATH=src

echo "TEST_NG_CONSERVATIVE_BREAKOUT_M1_ON_SIGNAL_BAR_V1_START"

python -m py_compile src/finam_core/strategy/futures/ng_conservative_breakout_m1.py

python - <<'PY'
from finam_core.strategy.futures.ng_conservative_breakout_m1 import NgConservativeBreakoutM1

s = NgConservativeBreakoutM1(symbol="NGN6@RTSX")
assert hasattr(s, "on_signal_bar"), "on_signal_bar missing"

print("NG_ON_SIGNAL_BAR_EXISTS_OK")
PY

echo "TEST_NG_CONSERVATIVE_BREAKOUT_M1_ON_SIGNAL_BAR_V1_OK"
