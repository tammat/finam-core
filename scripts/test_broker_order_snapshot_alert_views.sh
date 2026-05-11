#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core

test -f sql/20260511_broker_order_snapshot_alert_views.sql

grep -q "ORDER_STATUS_WATCHING" sql/20260511_broker_order_snapshot_alert_views.sql
grep -q "ORDER_STATUS_EXECUTED" sql/20260511_broker_order_snapshot_alert_views.sql
grep -q "ORDER_STATUS_DISABLED" sql/20260511_broker_order_snapshot_alert_views.sql
grep -q "ORDER_STATUS_SL_EXECUTED" sql/20260511_broker_order_snapshot_alert_views.sql
grep -q "ORDER_STATUS_TP_EXECUTED" sql/20260511_broker_order_snapshot_alert_views.sql
grep -q "terminal_status THEN 'OK'" sql/20260511_broker_order_snapshot_alert_views.sql
grep -q "status = '21' THEN 'OK'" sql/20260511_broker_order_snapshot_alert_views.sql
grep -q "Статус Finam" sql/20260511_broker_order_snapshot_alert_views.sql

echo "BROKER_ORDER_SNAPSHOT_ALERT_VIEWS_TEST_OK"
