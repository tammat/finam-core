#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python - <<'PY'
from finam_core.reconciliation.managed_position_reconciliation import ManagedPositionReconciliation

issues = ManagedPositionReconciliation().check()

print("RECONCILIATION_ISSUES", len(issues))

for i in issues:
    print(
        "RECONCILIATION_ISSUE",
        f"symbol={i.symbol}",
        f"kind={i.kind}",
        f"broker_qty={i.broker_qty}",
        f"managed_qty={i.managed_qty}",
        f"message={i.message}",
    )

if issues:
    raise SystemExit(1)

print("MANAGED_POSITION_RECONCILIATION_OK")
PY
