#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core

REPO="src/finam_core/execution/protective_order_link_repository.py"
GATE="src/finam_core/execution/protective_duplicate_gate.py"
SCRIPT="src/scripts/place_protective_for_filled_entries.py"

grep -q "def has_existing_protective_order" "$REPO"
grep -q "PROTECTIVE_ORDER_DUPLICATE_CHECK_FAILED" "$REPO"

test -f "$GATE"
grep -q "class ProtectiveDuplicateGate" "$GATE"
grep -q "PROTECTIVE_DUPLICATE_BLOCK" "$GATE"
grep -q "PROTECTIVE_DUPLICATE_OK" "$GATE"

grep -q "ProtectiveDuplicateGate" "$SCRIPT"
grep -q "duplicate_allowed=" "$SCRIPT"
grep -q "duplicate_reason=" "$SCRIPT"

PYTHONPATH=src python - <<'PY'
from finam_core.execution.protective_duplicate_gate import ProtectiveDuplicateGate


class Repo:
    def __init__(self, exists):
        self.exists = exists

    def has_existing_protective_order(self, *, entry_order_id, protective_type):
        return self.exists


assert ProtectiveDuplicateGate(Repo(False)).check(entry_order_id="e1", protective_type="stop").allowed is True
blocked = ProtectiveDuplicateGate(Repo(True)).check(entry_order_id="e1", protective_type="stop")
assert blocked.allowed is False
assert blocked.reason == "PROTECTIVE_DUPLICATE_BLOCK"

print("PROTECTIVE_DUPLICATE_GATE_RUNTIME_OK")
PY

python -m py_compile "$REPO"
python -m py_compile "$GATE"
python -m py_compile "$SCRIPT"

echo "PROTECTIVE_DUPLICATE_PREVENTION_TEST_OK"
