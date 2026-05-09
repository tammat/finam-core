#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src
export DATABASE_URL="${DATABASE_URL:-postgresql://finam:finam@localhost:5432/finam_core}"

python - <<'PY'
from finam_core.execution.oms_dispatch_guard import OmsDispatchGuard

guard = OmsDispatchGuard()

intent = {
    "symbol": "NGH6@RTSX",
    "side": "BUY",
    "qty": 1.0,
    "price": 100.0,
    "strategy": "test_dispatch_guard",
    "ts": "20260509T1200",
}

d1 = guard.prepare(dict(intent))
d2 = guard.prepare(dict(intent))

assert d1.allowed is True, d1
assert d2.allowed is False, d2
assert d1.client_order_id == d2.client_order_id

guard.mark_sent(
    client_order_id=d1.client_order_id,
    broker_order_id="broker_test_002",
)

print("OMS_DISPATCH_GUARD_OK", d1.client_order_id)
PY
