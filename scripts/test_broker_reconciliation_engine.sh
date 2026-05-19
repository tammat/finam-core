#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile \
  src/finam_core/runtime/broker_reconciliation_engine.py \
  src/scripts/run_broker_reconciliation_engine.py

python - <<'PY'
from finam_core.runtime.broker_reconciliation_engine import BrokerReconciliationEngine

e = BrokerReconciliationEngine()

external = e.classify_position(
    symbol="SBER@MISX",
    broker_qty=100,
    bot_executed_qty=0,
    source="manual_or_finam",
)
assert external is not None
assert external.category == "EXTERNAL_BROKER_POSITION"
assert external.severity == "INFO"

mismatch = e.classify_position(
    symbol="SBER@MISX",
    broker_qty=100,
    bot_executed_qty=50,
    source="paper_execution_bridge",
)
assert mismatch is not None
assert mismatch.category == "BROKER_RUNTIME_POSITION_MISMATCH"
assert mismatch.severity == "HIGH"

ok = e.classify_position(
    symbol="SBER@MISX",
    broker_qty=100,
    bot_executed_qty=100,
    source="paper_execution_bridge",
)
assert ok is None

print("OK: broker reconciliation engine")
PY

grep -q "BROKER_RECONCILIATION_SUMMARY" src/scripts/run_broker_reconciliation_engine.py
echo "OK: broker reconciliation summary"
