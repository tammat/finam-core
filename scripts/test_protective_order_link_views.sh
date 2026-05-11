#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core

test -f sql/20260511_protective_order_link_views.sql

grep -q "v_protective_order_links_grafana" sql/20260511_protective_order_link_views.sql
grep -q "v_protective_order_unprotected_entries_grafana" sql/20260511_protective_order_link_views.sql
grep -q "PROTECTED" sql/20260511_protective_order_link_views.sql
grep -q "UNPROTECTED" sql/20260511_protective_order_link_views.sql
grep -q "MISSING_STOP_TAKE_LINK" sql/20260511_protective_order_link_views.sql
grep -q "protective_order_links" sql/20260511_protective_order_link_views.sql
grep -q "ts AS time" sql/20260511_protective_order_link_views.sql
grep -q "DD-MM-YYYY HH24:MI:SS" sql/20260511_protective_order_link_views.sql

echo "PROTECTIVE_ORDER_LINK_VIEWS_TEST_OK"
