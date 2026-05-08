#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src
export EXECUTION_ENABLED=0
export REAL_TRADING_ENABLED=0

python - <<'PY'
from finam_core.execution.managed_position_service import ManagedPositionService
from finam_core.reconciliation.active_orders_reconciliation import ActiveOrdersReconciliation
from finam_core.adapters.grpc.orders_client import FinamOrdersClient

managed = ManagedPositionService()
managed.restore_from_repository()

orders_client = FinamOrdersClient()
issues = ActiveOrdersReconciliation(
    orders_client=orders_client,
    managed_service=managed,
).check()

print("ACTIVE_ORDER_RECONCILIATION_ISSUES", len(issues))

for i in issues:
    print(
        "ACTIVE_ORDER_ISSUE",
        f"symbol={i.symbol}",
        f"kind={i.kind}",
        f"order_id={i.order_id}",
        f"message={i.message}",
    )

critical = [
    i for i in issues
    if not i.kind.startswith("missing_")
]

if critical:
    raise SystemExit(1)

if issues:
    print("ACTIVE_ORDERS_RECONCILIATION_WARNINGS_ONLY")
else:
    print("ACTIVE_ORDERS_RECONCILIATION_OK")
PY
