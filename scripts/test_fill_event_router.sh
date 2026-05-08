#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src
export TRADE_MANAGEMENT_ENABLED=1
export STOP_REPLACE_LIVE=0

python - <<'PY'
from finam_core.execution.trade_management_service import TradeManagementService
from finam_core.execution.fill_event_router import FillEventRouter

svc = TradeManagementService()
router = FillEventRouter(svc)

r = router.on_fill({
    "symbol": "BRM6",
    "side": "BUY",
    "qty": 1,
    "client_order_id": "BRM6_TP1",
    "stop_order_id": "old-stop-br",
})

assert r is not None
assert r.status == "dry_run"
assert r.new_stop == 98.32

r2 = router.on_fill({
    "symbol": "BRM6",
    "side": "BUY",
    "qty": 1,
    "client_order_id": "BRM6_TP1",
    "stop_order_id": "old-stop-br",
})

assert r2 is None

r3 = router.on_fill({
    "symbol": "BRM6",
    "side": "BUY",
    "qty": 1,
    "client_order_id": "BRM6_TP2",
})

assert r3 is None

print("FILL_EVENT_ROUTER_OK")
PY
