#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core

test -f sql/20260511_order_reconciliation_views.sql

grep -q "v_order_reconciliation_runs_grafana" sql/20260511_order_reconciliation_views.sql
grep -q "v_order_reconciliation_issues_grafana" sql/20260511_order_reconciliation_views.sql
grep -q "order_reconciliation_runs" sql/20260511_order_reconciliation_views.sql
grep -q "order_reconciliation_issues" sql/20260511_order_reconciliation_views.sql
grep -q "DD-MM-YYYY HH24:MI:SS" sql/20260511_order_reconciliation_views.sql
grep -q "ts AS time" sql/20260511_order_reconciliation_views.sql

echo "ORDER_RECONCILIATION_VIEWS_TEST_OK"
