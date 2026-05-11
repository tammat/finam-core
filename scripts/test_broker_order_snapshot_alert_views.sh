#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core

test -f sql/20260511_broker_order_snapshot_alert_views.sql

grep -q "v_broker_order_snapshot_alerts_grafana" sql/20260511_broker_order_snapshot_alert_views.sql
grep -q "ALERT_EMPTY_SYMBOL" sql/20260511_broker_order_snapshot_alert_views.sql
grep -q "ALERT_INVALID_SIDE" sql/20260511_broker_order_snapshot_alert_views.sql
grep -q "ALERT_ZERO_QTY_ACTIVE_STATUS" sql/20260511_broker_order_snapshot_alert_views.sql
grep -q "ALERT_REMAINING_QTY" sql/20260511_broker_order_snapshot_alert_views.sql
grep -q "ALERT_UNKNOWN_STATUS" sql/20260511_broker_order_snapshot_alert_views.sql
grep -q "DISTINCT ON (order_id)" sql/20260511_broker_order_snapshot_alert_views.sql
grep -q "ts AS time" sql/20260511_broker_order_snapshot_alert_views.sql

echo "BROKER_ORDER_SNAPSHOT_ALERT_VIEWS_TEST_OK"
