#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core

test -f sql/20260511_order_reconciliation_alert_views.sql

grep -q "v_order_reconciliation_alerts_grafana" sql/20260511_order_reconciliation_alert_views.sql
grep -q "ALERT_RECONCILIATION_ISSUES" sql/20260511_order_reconciliation_alert_views.sql
grep -q "ALERT_RECONCILIATION_STATUS" sql/20260511_order_reconciliation_alert_views.sql
grep -q "issues_count > 0 OR status <> 'OK'" sql/20260511_order_reconciliation_alert_views.sql
grep -q "ts AS time" sql/20260511_order_reconciliation_alert_views.sql
grep -q "DD-MM-YYYY HH24:MI:SS" sql/20260511_order_reconciliation_alert_views.sql

echo "ORDER_RECONCILIATION_ALERT_VIEWS_TEST_OK"
