#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python - <<'PY'
from finam_core.execution.broker_capabilities_gate import BrokerCapabilities, BrokerCapabilitiesGate

knur = BrokerCapabilities(
    category="KNUR",
    allow_api_orders=True,
    allow_long=True,
    allow_short=False,
    allow_margin=False,
    allow_futures=False,
)

gate = BrokerCapabilitiesGate(knur)

ok, reason = gate.validate_order(instrument_type="STOCK", side="BUY", qty=1)
assert ok, reason

ok, reason = gate.validate_order(instrument_type="STOCK", side="SELL", qty=1)
assert not ok
assert reason == "short_forbidden"

ok, reason = gate.validate_order(instrument_type="FUTURE", side="BUY", qty=1)
assert not ok
assert reason == "futures_forbidden"

print("OK: BrokerCapabilitiesGate")
PY
