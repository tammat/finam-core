#!/usr/bin/env bash
set -euo pipefail

grep -q "AT TIME ZONE 'Europe/Moscow'" src/scripts/analytics/build_intraday_pnl.py
grep -q "AT TIME ZONE 'Europe/Moscow'" scripts/create_today_pnl_views_from_intraday.sql
grep -q "TZ=Europe/Moscow" scripts/run_intraday_pnl_today.sh

python -m py_compile src/scripts/analytics/build_intraday_pnl.py

echo "INTRADAY_PNL_MSK_DATE_TEST_OK"
