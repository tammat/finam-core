#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile \
  src/finam_core/runtime/portfolio_reconciliation_engine.py \
  src/scripts/run_portfolio_reconciliation_engine.py

python - <<'PY'
from finam_core.runtime.portfolio_reconciliation_engine import (
    PortfolioReconciliationEngine,
)

e = PortfolioReconciliationEngine()

assert e.check_position_vs_lifecycle(
    symbol="SBER",
    position_qty=1,
    lifecycle_qty=2,
) is not None

assert e.check_execution_vs_position(
    symbol="SBER",
    executed_qty=1,
    position_qty=2,
) is not None

assert e.check_orphan_position(
    symbol="SBER",
    position_qty=1,
    lifecycle_exists=False,
) is not None

assert e.check_orphan_lifecycle(
    symbol="SBER",
    lifecycle_qty=1,
    position_exists=False,
) is not None

print("OK: portfolio reconciliation engine")
PY

grep -q "paper_execution_bridge" src/scripts/run_portfolio_reconciliation_engine.py
grep -q "is_runtime_owned" src/scripts/run_portfolio_reconciliation_engine.py

echo "OK: portfolio reconciliation ownership filtering"
