#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile \
  src/finam_core/strategy/signal_router.py \
  src/finam_core/strategy/quote_signal_processor.py \
  src/finam_core/pipelines/paper_pipeline.py

python - <<'PY'
from finam_core.strategy.signal_router import SignalRouter, SignalRouteInput

class Q:
    def process(self, data):
        assert data.symbol == "BRM6@RTSX"
        assert isinstance(data.state, dict)
        return None

r = SignalRouter(Q())

x = r.route(SignalRouteInput(symbol="BRM6@RTSX", state={"price": 100}))
assert x.allowed is False
assert x.reason == "no_signal"

x = r.route({"symbol": "BRM6@RTSX", "state": {"price": 100}})
assert x.allowed is False

x = r.route({"state": {"price": 100}})
assert x.allowed is False
assert x.reason == "missing_symbol"

print("OK: signal router compile")
PY
