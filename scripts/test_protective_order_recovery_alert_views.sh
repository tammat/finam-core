#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core

test -f sql/20260511_protective_order_recovery_alert_views.sql

grep -q "v_protective_order_recovery_alerts_grafana" sql/20260511_protective_order_recovery_alert_views.sql
grep -q "PROTECTIVE_LINK_UNPROTECTED_ENTRY" sql/20260511_protective_order_recovery_alert_views.sql
grep -q "open_entry_has_no_stop_or_take_link" sql/20260511_protective_order_recovery_alert_views.sql
grep -q "RECOVERY_REQUIRED" sql/20260511_protective_order_recovery_alert_views.sql
grep -q "protective_order_links" sql/20260511_protective_order_recovery_alert_views.sql
grep -q "ts AS time" sql/20260511_protective_order_recovery_alert_views.sql
grep -q "DD-MM-YYYY HH24:MI:SS" sql/20260511_protective_order_recovery_alert_views.sql

echo "PROTECTIVE_ORDER_RECOVERY_ALERT_VIEWS_TEST_OK"
