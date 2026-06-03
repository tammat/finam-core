#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core

PY_BIN="${PY_BIN:-/opt/finam-core/venv/bin/python}"
[[ -x "$PY_BIN" ]] || PY_BIN="$(command -v python3)"

echo "TEST_SIGNAL_ATTRIBUTION_CLEANUP_V1_START"

"$PY_BIN" -m py_compile src/finam_core/signals/signal_intent.py

grep -q "SIGNAL_ATTRIBUTION_CLEANUP_V1" src/finam_core/signals/signal_intent.py

PYTHONPATH=src "$PY_BIN" - <<'PY'
from finam_core.signals.signal_intent import SignalIntent

s = SignalIntent.from_dict({
    "symbol": "NGN6@RTSX",
    "side": "BUY",
    "qty": 1,
    "strategy": "UNKNOWN_STRATEGY",
    "features": {"strategy": "NG_CONSERVATIVE_BREAKOUT_M1"},
})

assert s.strategy == "NG_CONSERVATIVE_BREAKOUT_M1", s.strategy
assert "UNKNOWN_STRATEGY" not in s.signal_id, s.signal_id
assert "NG_CONSERVATIVE_BREAKOUT_M1" in s.signal_id, s.signal_id
print("SIGNAL_ATTRIBUTION_CLEANUP_V1_RUNTIME_OK")
PY

echo "TEST_SIGNAL_ATTRIBUTION_CLEANUP_V1_OK"
