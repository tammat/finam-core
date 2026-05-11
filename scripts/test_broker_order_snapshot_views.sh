#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core

test -f sql/20260511_broker_order_snapshot_views.sql

grep -q "v_broker_order_snapshots_recent_grafana" sql/20260511_broker_order_snapshot_views.sql
grep -q "v_broker_order_snapshots_active_grafana" sql/20260511_broker_order_snapshot_views.sql
grep -q "broker_order_snapshots" sql/20260511_broker_order_snapshot_views.sql
grep -q "DISTINCT ON (order_id)" sql/20260511_broker_order_snapshot_views.sql
grep -q "remaining_qty" sql/20260511_broker_order_snapshot_views.sql
grep -q "ts AS time" sql/20260511_broker_order_snapshot_views.sql

echo "BROKER_ORDER_SNAPSHOT_VIEWS_TEST_OK"
