#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python - <<'PY'
from finam_core.execution.broker_reconciliation import BrokerReconciliationEngine

e = BrokerReconciliationEngine()

r = e.check_position("BRM6@RTSX", 2, 2)
assert r.ok is True, r
assert r.reason == "RECONCILIATION_OK", r

r = e.check_position("BRM6@RTSX", 2, 3)
assert r.ok is False, r
assert r.reason == "RECONCILIATION_MISMATCH", r

print("BROKER_RECONCILIATION_OK")
PY
