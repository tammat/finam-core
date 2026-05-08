#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python - <<'PY'
from finam_core.execution.stop_replacement_engine import (
    StopReplacementEngine,
    StopReplacementRequest,
)


class DummyOrdersClient:
    def __init__(self):
        self.cancelled = []
        self.placed = []

    def cancel_order(self, order_id):
        self.cancelled.append(order_id)

    def place_stop_order(self, **kwargs):
        self.placed.append(kwargs)
        return {"order_id": "new-stop-1"}


req = StopReplacementRequest(
    symbol="BRM6",
    stop_order_id="old-stop-1",
    new_stop=98.32,
    qty=1,
    side="BUY",
    reason="TP1 filled: move to breakeven",
)

dry = StopReplacementEngine(DummyOrdersClient(), dry_run=True)
r1 = dry.replace_stop(req)
assert r1.success is True
assert r1.status == "dry_run"

r2 = dry.replace_stop(req)
assert r2.success is True
assert r2.status == "duplicate_ignored"

client = DummyOrdersClient()
live = StopReplacementEngine(client, dry_run=False)
r3 = live.replace_stop(req)
assert r3.success is True
assert r3.status == "replaced"
assert client.cancelled == ["old-stop-1"]
assert client.placed[0]["symbol"] == "BRM6"
assert client.placed[0]["stop_price"] == 98.32

print("STOP_REPLACEMENT_ENGINE_OK")
PY
