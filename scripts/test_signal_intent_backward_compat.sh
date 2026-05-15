#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile src/finam_core/signals/signal_intent.py

python - <<'PY'
from finam_core.signals.signal_intent import SignalIntent

intent = SignalIntent(
    symbol="SBER@MISX",
    side="BUY",
)

assert intent.strategy == "UNKNOWN_STRATEGY"
assert intent.side == "BUY"
assert intent.signal_id.startswith("sig-UNKNOWN_STRATEGY-SBER@MISX-")

print("OK: SignalIntent backward compatibility without strategy")
PY
