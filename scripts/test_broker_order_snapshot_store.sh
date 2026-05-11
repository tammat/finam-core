#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core

test -f sql/20260511_broker_order_snapshots.sql
test -f src/finam_core/reconciliation/broker_order_snapshot_store.py

grep -q "CREATE TABLE IF NOT EXISTS broker_order_snapshots" sql/20260511_broker_order_snapshots.sql
grep -q "idx_broker_order_snapshots_order_id_ts" sql/20260511_broker_order_snapshots.sql
grep -q "class BrokerOrderSnapshotStore" src/finam_core/reconciliation/broker_order_snapshot_store.py
grep -q "BROKER_ORDER_SNAPSHOT_STORE_FAILED" src/finam_core/reconciliation/broker_order_snapshot_store.py
grep -q "BrokerOrderSnapshotStore" src/scripts/reconcile_order_acks.py
grep -q "broker_snapshots_saved" src/scripts/reconcile_order_acks.py

python -m py_compile src/finam_core/reconciliation/broker_order_snapshot_store.py
python -m py_compile src/scripts/reconcile_order_acks.py

echo "BROKER_ORDER_SNAPSHOT_STORE_TEST_OK"
