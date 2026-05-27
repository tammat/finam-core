#!/usr/bin/env bash
set -euo pipefail

test -f scripts/create_today_rejected_trades_views.sql

grep -q "v_today_rejected_trades_ru" scripts/create_today_rejected_trades_views.sql
grep -q "v_today_rejected_trades_summary_ru" scripts/create_today_rejected_trades_views.sql
grep -q "invalid_reason" scripts/create_today_rejected_trades_views.sql
grep -q "AT TIME ZONE 'Europe/Moscow'" scripts/create_today_rejected_trades_views.sql
grep -q "is_invalid = true" scripts/create_today_rejected_trades_views.sql

echo "TODAY_REJECTED_TRADES_VIEWS_TEST_OK"
