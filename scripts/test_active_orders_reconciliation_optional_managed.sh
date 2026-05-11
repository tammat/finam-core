#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core

grep -q "ManagedPositionService может быть не подключён" src/finam_core/reconciliation/active_orders_reconciliation.py
grep -q "self.managed is None" src/finam_core/reconciliation/active_orders_reconciliation.py
grep -q "getattr(self.managed, \"repository\", None) is None" src/finam_core/reconciliation/active_orders_reconciliation.py

python -m py_compile src/finam_core/reconciliation/active_orders_reconciliation.py

echo "ACTIVE_ORDERS_RECONCILIATION_OPTIONAL_MANAGED_TEST_OK"
