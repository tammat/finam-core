#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python - <<'PY'
from finam_core.reconciliation.portfolio_reconciliation_repair import PortfolioReconciliationRepair

repair = PortfolioReconciliationRepair(qty_tolerance=1e-9)

ok = repair.evaluate(symbol="SBER@MISX", local_qty=1, broker_qty=1)
assert ok.status == "OK", ok
assert ok.repaired_qty == 1.0, ok

halt = repair.evaluate(symbol="SBER@MISX", local_qty=1, broker_qty=2, allow_repair=False)
assert halt.status == "HALT_REQUIRED", halt
assert halt.repaired_qty is None, halt

fixed = repair.evaluate(symbol="SBER@MISX", local_qty=1, broker_qty=2, allow_repair=True)
assert fixed.status == "REPAIRED", fixed
assert fixed.repaired_qty == 2.0, fixed

zero_fix = repair.evaluate(symbol="GAZP@MISX", local_qty=3, broker_qty=0, allow_repair=True)
assert zero_fix.status == "REPAIRED", zero_fix
assert zero_fix.repaired_qty == 0.0, zero_fix

print("OK: PortfolioReconciliationRepair")
PY
