#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python - <<'PY'
import os

from finam_core.execution.broker_capabilities_gate import BrokerCapabilities, BrokerCapabilitiesGate
from finam_core.execution.execution_dispatcher import ExecutionDispatcher


class FakePaper:
    def place_limit_order(self, **kwargs):
        return {"status": "PAPER_ACCEPTED", **kwargs}


class FakeLive:
    def place_limit_order(self, **kwargs):
        return {"status": "LIVE_CALLED", **kwargs}


gate = BrokerCapabilitiesGate(
    BrokerCapabilities(
        category="KSUR",
        allow_api_orders=True,
        allow_long=True,
        allow_short=True,
        allow_margin=False,
        allow_futures=True,
    )
)

dispatcher = ExecutionDispatcher(
    paper_executor=FakePaper(),
    live_executor=FakeLive(),
    capabilities_gate=gate,
)

os.environ["EXECUTION_MODE"] = "paper"
r = dispatcher.place_limit_order(symbol="SBER@MISX", side="BUY", qty=1, limit_price=300.0)
assert r["status"] == "PAPER_ACCEPTED", r

os.environ["EXECUTION_MODE"] = "real"
r = dispatcher.place_limit_order(symbol="SBER@MISX", side="BUY", qty=1, limit_price=300.0)
assert r["status"] == "LIVE_CALLED", r

knur_gate = BrokerCapabilitiesGate(
    BrokerCapabilities(
        category="KNUR",
        allow_api_orders=True,
        allow_long=True,
        allow_short=False,
        allow_margin=False,
        allow_futures=False,
    )
)

dispatcher = ExecutionDispatcher(
    paper_executor=FakePaper(),
    live_executor=FakeLive(),
    capabilities_gate=knur_gate,
)

os.environ["EXECUTION_MODE"] = "real"
r = dispatcher.place_limit_order(symbol="NGM6@RTSX", side="BUY", qty=1, limit_price=2.5, instrument_type="FUTURE")
assert r["status"] == "REJECTED", r
assert r["reason"] == "futures_forbidden", r

print("OK: ExecutionDispatcher live-route protected")
PY
