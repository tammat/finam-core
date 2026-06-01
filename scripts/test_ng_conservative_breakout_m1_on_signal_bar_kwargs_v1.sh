#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core
export PYTHONPATH=src

echo "TEST_NG_CONSERVATIVE_BREAKOUT_M1_ON_SIGNAL_BAR_KWARGS_V1_START"

python -m py_compile src/finam_core/strategy/futures/ng_conservative_breakout_m1.py

python - <<'PY'
from finam_core.strategy.futures.ng_conservative_breakout_m1 import NgConservativeBreakoutM1

s = NgConservativeBreakoutM1(symbol="NGN6@RTSX")

assert hasattr(s, "on_signal_bar")

result = s.on_signal_bar(
    ts="2026-05-31T12:55:00+03:00",
    open=3.50,
    high=3.55,
    low=3.49,
    close=3.54,
    volume=1.0,
)

print("NG_ON_SIGNAL_BAR_KWARGS_OK", result)
PY

echo "TEST_NG_CONSERVATIVE_BREAKOUT_M1_ON_SIGNAL_BAR_KWARGS_V1_OK"
