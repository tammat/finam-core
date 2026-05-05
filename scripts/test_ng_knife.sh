#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."
export PYTHONPATH=src

python -m py_compile \
  src/finam_core/strategy/ng_event_filters.py \
  src/finam_core/strategy/ng_volatility_breakout.py

python - <<'PY'
from finam_core.strategy.ng_event_filters import Candle, KnifeState, is_knife_bar

knife = Candle(open=3.0, high=3.18, low=2.99, close=3.17)
normal = Candle(open=3.0, high=3.02, low=2.99, close=3.01)

assert is_knife_bar(knife, prev_close=3.0, atr=0.05) is True
assert is_knife_bar(normal, prev_close=3.0, atr=0.05) is False

st = KnifeState(cooldown_bars=3)
st.on_bar(True, side="UP")
assert st.is_blocked() is True
assert st.cooldown_left == 3

st.on_bar(False)
assert st.cooldown_left == 2

print("NG_KNIFE_TEST_OK")
PY
