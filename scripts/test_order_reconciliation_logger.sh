#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core

test -f sql/20260511_order_reconciliation_runs.sql
test -f src/finam_core/reconciliation/order_reconciliation_logger.py

grep -q "CREATE TABLE IF NOT EXISTS order_reconciliation_runs" sql/20260511_order_reconciliation_runs.sql
grep -q "CREATE TABLE IF NOT EXISTS order_reconciliation_issues" sql/20260511_order_reconciliation_runs.sql
grep -q "idx_order_reconciliation_runs_ts" sql/20260511_order_reconciliation_runs.sql
grep -q "idx_order_reconciliation_issues_order_id" sql/20260511_order_reconciliation_runs.sql

grep -q "class OrderReconciliationLogger" src/finam_core/reconciliation/order_reconciliation_logger.py
grep -q "ORDER_RECONCILIATION_LOG_FAILED" src/finam_core/reconciliation/order_reconciliation_logger.py
grep -q "OrderReconciliationLogger" src/scripts/reconcile_order_acks.py
grep -q "run_id=" src/scripts/reconcile_order_acks.py

python -m py_compile src/finam_core/reconciliation/order_reconciliation_logger.py
python -m py_compile src/scripts/reconcile_order_acks.py

echo "ORDER_RECONCILIATION_LOGGER_TEST_OK"
