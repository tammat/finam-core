#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src
export TRADE_MANAGEMENT_ENABLED=1
export STOP_REPLACE_LIVE=0

python - <<'PY'
from finam_core.execution.trade_management_service import TradeManagementService

svc = TradeManagementService()

r = svc.on_take_profit_fill(
    symbol="BRM6",
    tp_index=1,
    qty=1,
    side="BUY",
    stop_order_id="old-stop-br",
)

assert r is not None
assert r.success is True
assert r.status == "dry_run"
assert r.new_stop == 98.32

r2 = svc.on_take_profit_fill(
    symbol="BRM6",
    tp_index=1,
    qty=1,
    side="BUY",
    stop_order_id="old-stop-br",
)

assert r2 is None

print("TRADE_MANAGEMENT_SERVICE_OK")
PY
