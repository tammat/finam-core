#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core

test -f src/finam_core/reconciliation/protective_order_recovery_check.py
test -f src/scripts/check_protective_order_recovery.py

grep -q "class ProtectiveOrderRecoveryCheck" src/finam_core/reconciliation/protective_order_recovery_check.py
grep -q "PROTECTIVE_LINK_UNPROTECTED_ENTRY" src/finam_core/reconciliation/protective_order_recovery_check.py
grep -q "PROTECTIVE_ORDER_RECOVERY_CHECK" src/scripts/check_protective_order_recovery.py
grep -q "PROTECTIVE_ORDER_RECOVERY_ISSUE" src/scripts/check_protective_order_recovery.py

python -m py_compile src/finam_core/reconciliation/protective_order_recovery_check.py
python -m py_compile src/scripts/check_protective_order_recovery.py

echo "PROTECTIVE_ORDER_RECOVERY_CHECK_TEST_OK"
