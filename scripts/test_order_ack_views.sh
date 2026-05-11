#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core

test -f sql/20260511_order_ack_views.sql

grep -q "v_order_acks_recent_grafana" sql/20260511_order_ack_views.sql
grep -q "v_order_acks_reconciliation_grafana" sql/20260511_order_ack_views.sql
grep -q "NO_ORDER_ID" sql/20260511_order_ack_views.sql
grep -q "ACK_OK" sql/20260511_order_ack_views.sql
grep -q "DD-MM-YYYY HH24:MI:SS" sql/20260511_order_ack_views.sql
grep -q "ts AS time" sql/20260511_order_ack_views.sql

echo "ORDER_ACK_VIEWS_TEST_OK"
